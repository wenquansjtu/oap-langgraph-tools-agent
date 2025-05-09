import logging
import os
import requests
from typing import Dict, Optional, Any
from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_store

def get_mcp_access_token(
    supabase_token: str,
    base_token_exchange_url: str,
) -> Optional[Dict[str, Any]]:
    """
    Exchange a Supabase token for an MCP access token.
    
    Args:
        supabase_token: The Supabase token to exchange
        base_token_exchange_url: The base URL for the token exchange service
        
    Returns:
        The token data as a dictionary if successful, None otherwise
    """
    try:
        # Exchange Supabase token for MCP access token
        form_data = {
            "client_id": "mcp_default",
            "subject_token": supabase_token,
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "resource": f"{base_token_exchange_url}/mcp",
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        }
        
        token_response = requests.post(
            f"{base_token_exchange_url}/oauth/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=form_data
        )
        
        if token_response.status_code == 200:
            token_data = token_response.json()
            return token_data
        else:
            logging.error(f"Token exchange failed: {token_response.text}")
    except Exception as e:
        logging.error(f"Error during token exchange: {e}")
    
    return None

def get_tokens(config: RunnableConfig) :
    store = get_store()
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        print("Thread ID not found in config")
        return None
    
    user_id = config.get("metadata", {}).get("owner")
    if not user_id:
        print("User ID not found in metadata")
        return None
    
    tokens = store.get([user_id, "tokens", thread_id], "data")
    if not tokens:
        return None
    
    return tokens.value

def set_tokens(config: RunnableConfig, tokens: dict[str, Any]):
    store = get_store()
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        print("Thread ID not found in config")
        return
    
    user_id = config.get("metadata", {}).get("owner")
    if not user_id:
        print("User ID not found in metadata")
        return
    
    store.put([user_id, "tokens", thread_id], "data", tokens)
    return

def fetch_tokens(config: RunnableConfig) -> dict[str, Any]:
    """
    Fetch MCP access token if it doesn't already exist in the store.
    
    Args:
        config: The runnable configuration
        
    Raises:
        ValueError: If required configuration is missing
    """

    base_mcp_token_exchange_url = os.environ.get("BASE_MCP_TOKEN_EXCHANGE_URL")
    if not base_mcp_token_exchange_url:
        print("MCP token exchange URL is required")
        return None
    
    current_tokens = get_tokens(config)
    if current_tokens:
        return current_tokens
    
    supabase_token = config.get("x-supabase-access-token")
    if not supabase_token:
        print("Supabase access token is required")
        return None
    
    mcp_config = config.get("configurable", {}).get("mcp_config")
    if not mcp_config:
        print("MCP config is required")
        return None
    
    mcp_tokens = get_mcp_access_token(
        supabase_token,
        base_mcp_token_exchange_url
    )
    
    set_tokens(config, mcp_tokens)
    return mcp_tokens
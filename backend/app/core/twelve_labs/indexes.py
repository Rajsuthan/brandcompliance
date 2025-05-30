"""Module for managing Twelve Labs video indexes.

This module provides functions to create and manage video indexes in the Twelve Labs platform.
"""

from typing import Dict, List, Optional, Any, Union

from twelvelabs import TwelveLabs

# Let's use direct TwelveLabs client functionality instead of importing specific modules
# This makes our code more resilient to SDK changes

from .config import get_client


def create_index(
    index_name: str,
    models: Optional[List[Dict[str, Any]]] = None,
    addons: Optional[List[str]] = None,
    client: Optional[TwelveLabs] = None
) -> Union[str, None]:
    """Create a new index for video processing.
    
    Args:
        index_name: Name for the new index
        models: List of model configurations to use. Defaults to Marengo2.7 with visual and audio options.
        addons: List of addons to enable. Defaults to ["thumbnail"].
        client: Optional TwelveLabs client instance. If not provided, one will be created.
        
    Returns:
        Index ID if successful, None if failed
        
    Example:
        >>> index_id = create_index("brand_compliance_videos")
    """
    # Default model configuration if none provided
    if models is None:
        models = [
            {
                "model_name": "marengo2.7",
                "model_options": ["visual", "audio"]
            }
        ]
    
    # Default addons if none provided
    if addons is None:
        addons = ["thumbnail"]
    
    # Get client if not provided
    client = client or get_client()
    
    try:
        # Direct API call without assuming indexes attribute exists
        # This approach works with the client's direct methods
        try:
            # Try to find the appropriate method for creating an index
            if hasattr(client, 'create_index'):
                index = client.create_index(index_name=index_name, models=models, addons=addons)
            else:
                # Look for other potential methods if create_index doesn't exist
                for method_name in dir(client):
                    if 'create' in method_name.lower() and 'index' in method_name.lower():
                        method = getattr(client, method_name)
                        if callable(method):
                            index = method(name=index_name, models=models, addons=addons)
                            break
                else:
                    # If we didn't find a suitable method
                    print("No suitable method found to create index")
                    return None
            
            # Handle different response structures by checking for attributes
            if hasattr(index, 'id'):
                return index.id
            elif hasattr(index, '_id'):
                return index._id
            elif isinstance(index, dict) and 'id' in index:
                return index['id']
            else:
                # As a last resort, try to get the first attribute that might be an ID
                for attr in dir(index):
                    if attr.endswith('id') or attr.endswith('_id'):
                        return getattr(index, attr)
                return str(index)  # Return string representation as fallback
        except Exception as inner_e:
            print(f"Inner error creating index: {inner_e}")
            return None
    except Exception as e:
        print(f"Error creating index: {e}")
        return None


def list_indexes(client: Optional[TwelveLabs] = None) -> List[Dict[str, Any]]:
    """List all available indexes.
    
    Args:
        client: Optional TwelveLabs client instance. If not provided, one will be created.
        
    Returns:
        List of index data objects/dicts
    """
    # Get client if not provided
    client = client or get_client()
    
    try:
        # Direct approach without assuming indexes attribute exists
        if hasattr(client, 'list_indexes'):
            # First try a direct list_indexes method
            try:
                indexes = client.list_indexes()
                if indexes is None:
                    return []
            except Exception as e:
                print(f"Error calling list_indexes: {e}")
                return []
        else:
            # Look for other methods that might list indexes
            for method_name in dir(client):
                if ('list' in method_name.lower() or 'get' in method_name.lower()) and 'index' in method_name.lower():
                    try:
                        method = getattr(client, method_name)
                        if callable(method):
                            indexes = method()
                            if indexes:
                                break
                    except Exception:
                        continue
            else:
                print("No suitable method found to list indexes")
                return []
        
        # Convert results to a standard format
        result = []
        if indexes:
            for index in indexes:
                if isinstance(index, dict):
                    result.append(index)
                else:
                    # Try to convert object to dict
                    try:
                        result.append(index.__dict__)
                    except (AttributeError, TypeError):
                        # If all else fails, add whatever we have
                        result.append({"id": str(index), "object": index})
        
        return result
    except Exception as e:
        print(f"Error listing indexes: {e}")
        return []


def get_index(index_id: str, client: Optional[TwelveLabs] = None) -> Optional[Dict[str, Any]]:
    """Get details for a specific index.
    
    Args:
        index_id: ID of the index to retrieve
        client: Optional TwelveLabs client instance. If not provided, one will be created.
        
    Returns:
        Index data as dict if found, None otherwise
    """
    client = client or get_client()
    
    try:
        # Direct approach without assuming indexes attribute exists
        if hasattr(client, 'get_index'):
            try:
                index = client.get_index(index_id)
                if index is None:
                    return None
            except Exception as e:
                print(f"Error calling get_index: {e}")
                # Fall back to listing all indexes and finding the matching one
                return _find_index_in_list(index_id, client)
        else:
            # Look for other methods that might get an index
            for method_name in dir(client):
                if ('get' in method_name.lower() or 'retrieve' in method_name.lower()) and 'index' in method_name.lower():
                    try:
                        method = getattr(client, method_name)
                        if callable(method):
                            index = method(index_id)
                            if index:
                                break
                    except Exception:
                        continue
            else:
                # If no method found, try to find in list
                return _find_index_in_list(index_id, client)
        
        # Convert result to a standard format
        if isinstance(index, dict):
            return index
        else:
            # Try to convert object to dict
            try:
                return index.__dict__
            except (AttributeError, TypeError):
                # If all else fails, add whatever we have
                return {"id": index_id, "object": index}
                
    except Exception as e:
        print(f"Error getting index {index_id}: {e}")
        return None


def _find_index_in_list(index_id: str, client: TwelveLabs) -> Optional[Dict[str, Any]]:
    """Helper function to find an index by ID in a list of indexes.
    
    Args:
        index_id: ID of the index to find
        client: TwelveLabs client instance
        
    Returns:
        Index data as dict if found, None otherwise
    """
    indexes = list_indexes(client)
    for idx in indexes:
        if isinstance(idx, dict) and (idx.get('id') == index_id or idx.get('_id') == index_id):
            return idx
    return None


def delete_index(index_id: str, client: Optional[TwelveLabs] = None) -> bool:
    """Delete a specific index.
    
    Args:
        index_id: ID of the index to delete
        client: Optional TwelveLabs client instance. If not provided, one will be created.
        
    Returns:
        True if successful, False otherwise
    """
    client = client or get_client()
    
    try:
        # Direct approach without assuming indexes attribute exists
        if hasattr(client, 'delete_index'):
            try:
                client.delete_index(index_id)
                return True
            except Exception as e:
                print(f"Error calling delete_index: {e}")
                return False
        else:
            # Look for other methods that might delete an index
            for method_name in dir(client):
                if any(term in method_name.lower() for term in ['delete', 'remove', 'destroy']) and 'index' in method_name.lower():
                    try:
                        method = getattr(client, method_name)
                        if callable(method):
                            method(index_id)
                            return True
                    except Exception:
                        continue
            # If no suitable method found
            print(f"Could not find a way to delete index {index_id}")
            return False
    except Exception as e:
        print(f"Error deleting index {index_id}: {e}")
        return False

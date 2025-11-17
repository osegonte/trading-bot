"""
Configuration loader for modules
Loads and validates YAML configuration
"""
import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def load_module_config(config_path: str = 'config/modules.yaml') -> Dict[str, Any]:
    """
    Load module configuration from YAML file
    
    Args:
        config_path: Path to YAML config file
    
    Returns:
        Configuration dictionary
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {e}")
    
    # Validate structure
    if 'technical' not in config and 'fundamental' not in config:
        raise ValueError("Config must contain 'technical' or 'fundamental' section")
    
    logger.info(f"✅ Loaded config from {config_path}")
    return config


def get_enabled_modules(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Get only enabled modules from config
    
    Args:
        config: Full configuration dictionary
    
    Returns:
        Dictionary of enabled modules with their configs
    """
    enabled = {}
    
    for category in ['technical', 'fundamental']:
        if category not in config:
            continue
        
        for module_name, module_config in config[category].items():
            if module_config.get('enabled', True):
                enabled[module_name] = module_config
    
    logger.info(f"✅ Found {len(enabled)} enabled modules")
    return enabled


def save_module_config(config: Dict[str, Any], config_path: str = 'config/modules.yaml') -> None:
    """
    Save module configuration to YAML file
    
    Args:
        config: Configuration dictionary
        config_path: Path to save to
    """
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    logger.info(f"✅ Saved config to {config_path}")


def update_module_weight(module_name: str, new_weight: float, config_path: str = 'config/modules.yaml') -> None:
    """
    Update a module's weight in the config file
    
    Args:
        module_name: Name of module to update
        new_weight: New weight value (0-2.0)
        config_path: Path to config file
    """
    config = load_module_config(config_path)
    
    # Find and update module
    updated = False
    for category in ['technical', 'fundamental']:
        if category in config and module_name in config[category]:
            config[category][module_name]['weight'] = new_weight
            updated = True
            break
    
    if not updated:
        raise ValueError(f"Module not found: {module_name}")
    
    save_module_config(config, config_path)
    logger.info(f"✅ Updated {module_name} weight to {new_weight}")

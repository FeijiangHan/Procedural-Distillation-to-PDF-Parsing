from pathlib import Path
import json
from typing import Dict, Any, Optional
import time

class FileCache:
    """文件缓存管理器"""
    
    def __init__(self, cache_dir: Path, max_age: int = 3600):
        self.cache_dir = cache_dir
        self.max_age = max_age  # 缓存最大年龄(秒)
        self.cache_dir.mkdir(exist_ok=True)
        
    def get(self, key: str) -> Optional[Any]:
        """获取缓存的值"""
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None
            
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                
            # 检查缓存是否过期
            if time.time() - data['timestamp'] > self.max_age:
                cache_file.unlink()
                return None
                
            return data['value']
            
        except Exception:
            return None
            
    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        cache_file = self.cache_dir / f"{key}.json"
        
        data = {
            'timestamp': time.time(),
            'value': value
        }
        
        with open(cache_file, 'w') as f:
            json.dump(data, f)
            
    def clear(self) -> None:
        """清除所有缓存"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink() 
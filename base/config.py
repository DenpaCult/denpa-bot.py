import json

class Config():
    _instance: dict | None = None

    @classmethod
    def read_config(cls: type["Config"], config_file: str = "config.json") -> dict:
        '''
        returns a json of the config file
        '''
        if cls._instance:
            return cls._instance
    
        js: dict = {}
        with open(config_file) as f:
            js = json.loads(f.read())
        cls._instance = js
        return cls._instance
    

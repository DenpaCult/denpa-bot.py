import json

class config():
    _config = None
    @classmethod
    def read_config(cls, config_file: str = "config.json"):
        '''
        returns a json of the config file
        '''
        if cls._config:
            return cls._config
    
        js: dict = {}
        with open(config_file) as f:
            js = json.loads(f.read())
        cls._config = js
        return cls._config
    

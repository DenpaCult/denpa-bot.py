import json

class config():
    _config: dict | None = None

    @classmethod
    def read_config(cls: type["config"], config_file: str = "config.json") -> dict:
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
    

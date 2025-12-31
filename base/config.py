import json

class Config():
    _instance: dict | None = None

    @classmethod
    def read_config(cls: type["Config"], config_file: str = "persist/config.json") -> dict:
        '''
        returns a json of the config file
        '''
        if cls._instance:
            return cls._instance
    
        js: dict = {}
        with open(config_file, encoding="utf-8") as f:
            js = json.loads(f.read())
        cls._instance = js
        return cls._instance
    
    @classmethod
    def update_config(cls, new_config: dict, config_file: str = "persist/config.json"):
        """
        how to make this safe so it doesnt ruin the config file if wrong dict object is passed?
        """
        cls._instance = new_config
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(new_config, indent=4))

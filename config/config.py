import json

def read_config(config_file: str = "config.json"):
    '''
    returns a json of the config file
    '''
    js: dict = {}
    with open(config_file) as f:
        js = json.loads(f.read())
    return js


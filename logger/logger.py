from datetime import datetime
import inspect
import os

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN =	'\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    LIGHTGRAY = '\033[37m'
    RESET = '\033[0m'

class logger:
    
    _instance = None
    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def _get_formatted_time(self):
        time = datetime.now()
        formatted = time.strftime("%H:%M:%S")
        return formatted

    def _get_frame(self):
        frame = inspect.currentframe().f_back.f_back
        filename = os.path.basename(frame.f_code.co_filename)
        function = frame.f_code.co_name

        return (filename, function)



    def log(self, message: str):
        time = self._get_formatted_time()
        filename, function = self._get_frame()

        print(
            f'{bcolors.OKBLUE}{time}, '
            f'{bcolors.OKGREEN}{filename}@{function}:'
            f'\n\t{bcolors.OKCYAN}{message}{bcolors.RESET}'
        )
    
    def warn(self, message: str):
        time = self._get_formatted_time()
        filename, function = self._get_frame()

        print(
            f'WARN:{bcolors.OKBLUE}{time}, '
            f'{bcolors.YELLOW}{filename}@{function}:'
            f'\n\t{bcolors.WARNING}{message}{bcolors.RESET}'
        )

    def error(self, message: str):
        time = self._get_formatted_time()
        filename, function = self._get_frame()

        print(
            f'ERROR:{bcolors.RED}{time}, '
            f'{bcolors.FAIL}{filename}@{function}:'
            f'\n\t{bcolors.WARNING}{message}{bcolors.RESET}'
        )
    

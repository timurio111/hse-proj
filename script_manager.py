from multiprocessing import Process

from script import run


class ScriptManager:
    process: Process = Process()

    @staticmethod
    def run_subprocess():
        ScriptManager.kill_subprocess()
        ScriptManager.process = Process(target=run)
        ScriptManager.process.start()

    @staticmethod
    def kill_subprocess():
        if ScriptManager.process.is_alive():
            ScriptManager.process.kill()

    @staticmethod
    def check():
        if ScriptManager.process.exitcode:
            ScriptManager.process = Process()
            raise Exception('Camera exception')

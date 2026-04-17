import subprocess
import threading


class ManagedProcess:
    def __init__(self, command, cwd=None, env=None):
        self.command = command
        self.cwd = cwd
        self.env = env
        self.process = None

    def start(self, on_line, on_finished):
        def _run():
            self.process = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                env=self.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
            if self.process.stdout:
                for line in self.process.stdout:
                    on_line(line.rstrip())
            code = self.process.wait()
            on_finished(code)

        threading.Thread(target=_run, daemon=True).start()

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()

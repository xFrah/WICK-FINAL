import paramiko
import pysftp
from urllib.parse import urlparse
import os


class SFTP:
    def __init__(self, hostname, username, password, port=22):
        """Constructor Method"""
        # Set connection object to None (initial value)
        self.connection = paramiko.SSHClient()
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port

    def connect(self):
        """Connects to the sftp server and returns the sftp connection object"""

        try:
            self.connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.connection.connect(self.hostname, self.port, self.username, self.password)
        except Exception as err:
            raise Exception(err)
        finally:
            print(f"[SFTP] Connected to {self.hostname} as {self.username}.")

    def disconnect(self):
        """Closes the sftp connection"""
        self.connection.close()
        print(f"[SFTP] Disconnected from host {self.hostname}")

    def upload(self, source_local_path, remote_path):
        """
        Uploads the source files from local to the sftp server.
        """
        # upload files with paramiko
        try:
            sftp = self.connection.open_sftp()
            sftp.put(source_local_path, remote_path)
        except Exception as err:
            raise Exception(err)

    def upload_files(self, files, source_local_path, remote_path):
        try:
            sftp = self.connection.open_sftp()
        except Exception as err:
            return print(err)
        errors = 0
        last = 0
        for i, file in enumerate(files):
            try:
                sftp.put(os.path.join(source_local_path, file), os.path.join(remote_path, file))
            except Exception as err:
                print(f"[ERROR] Cause: {err}")
                errors += 1
            n = int(i / len(files) * 10)
            if n > last:
                print(f"{n*10}%", end="", flush=True)
                last = n
        return errors, len(files)

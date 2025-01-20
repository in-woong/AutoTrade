import os
import time
from datetime import datetime, timedelta

class CleanupManager:
    @staticmethod
    def clean_directory(directory, max_age_hours=24):
        """
        Cleans up files in a directory older than max_age_hours.

        Args:
            directory (str): Path to the directory.
            max_age_hours (int): Maximum file age in hours.
        """
        now = datetime.now()
        max_age = timedelta(hours=max_age_hours)

        if not os.path.exists(directory):
            return

        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_age = now - datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_age > max_age:
                    os.remove(file_path)

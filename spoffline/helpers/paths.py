import os
import tempfile


class DefaultPaths:
    @staticmethod
    def _init_path(*paths):
        requested_path = os.path.join(*paths)

        if not os.path.exists(requested_path):
            os.makedirs(requested_path)

        return requested_path

    @staticmethod
    def get_root_path():
        return DefaultPaths._init_path(
            tempfile.gettempdir(),
            'spoffline'
        )

    @staticmethod
    def get_temp_path():
        return DefaultPaths._init_path(
            DefaultPaths.get_root_path(),
            'temp'
        )

    @staticmethod
    def get_cache_path():
        return DefaultPaths._init_path(
            DefaultPaths.get_root_path(),
            'cache'
        )

    @staticmethod
    def get_download_path():
        return os.getcwd()

import pymysql

pymysql.install_as_MySQLdb()

# Monkey patch to bypass Django's mysqlclient version check
if not hasattr(pymysql, 'version_info') or pymysql.version_info < (2, 2, 1):
    pymysql.version_info = (2, 2, 1, "final", 0) 

# MySQLdb.version_info = (2, 2, 1, 'final', 0)

# Disable database version check because user has MariaDB 10.4 but Django wants 10.6
try:
    from django.db.backends.mysql.base import DatabaseWrapper
    DatabaseWrapper.check_database_version_supported = lambda self: None
    
    # Disable RETURNING clause for MariaDB < 10.5
    from django.db.backends.mysql.features import DatabaseFeatures
    DatabaseFeatures.can_return_columns_from_insert = property(lambda self: False)
    DatabaseFeatures.can_return_rows_from_bulk_insert = property(lambda self: False)
except ImportError:
    pass

# Fix for Django 4.2.27 + Python 3.14 compatibility issue with context copying
try:
    from django.template.context import BaseContext
    import copy
    
    original_copy = BaseContext.__copy__
    
    def patched_copy(self):
        """Patched __copy__ method to handle Python 3.14 slot restrictions"""
        from copy import copy as _copy
        duplicate = object.__new__(self.__class__)
        for k, v in self.__dict__.items():
            setattr(duplicate, k, _copy(v))
        if hasattr(self, 'dicts'):
            duplicate.dicts = self.dicts[:]
        return duplicate
    
    BaseContext.__copy__ = patched_copy
except Exception:
    pass

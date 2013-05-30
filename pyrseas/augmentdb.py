# -*- coding: utf-8 -*-
"""
    pyrseas.augmentdb
    ~~~~~~~~~~~~~~~~~

    An `AugmentDatabase` is initialized with a DbConnection object.
    It consists of two "dictionary" container objects, each holding
    various dictionary objects.  The `db` Dicts object (inherited from
    its parent class), defines the database schemas, including their
    tables and other objects, by querying the system catalogs.  The
    `adb` AugDicts object defines the augmentation schemas and the
    configuration objects based on the aug_map supplied to the `apply`
    method.
"""
from pyrseas.database import Database
from pyrseas.dbobject.language import Language
from pyrseas.augment.schema import AugSchemaDict
from pyrseas.augment.table import AugClassDict
from pyrseas.augment.column import CfgColumnDict
from pyrseas.augment.function import CfgFunctionDict, CfgFunctionSourceDict
from pyrseas.augment.trigger import CfgTriggerDict
from pyrseas.augment.audit import CfgAuditColumnDict


class AugmentDatabase(Database):
    """A database that is to be augmented"""

    class AugDicts(object):
        """A holder for dictionaries (maps) describing augmentations"""

        def __init__(self):
            """Initialize the various DbAugmentDict-derived dictionaries"""
            self.schemas = AugSchemaDict()
            self.tables = AugClassDict()
            self.columns = CfgColumnDict()
            self.funcsrcs = CfgFunctionSourceDict()
            self.functions = CfgFunctionDict()
            self.triggers = CfgTriggerDict()
            self.auditcols = CfgAuditColumnDict()

        def _link_refs(self):
            """Link related objects"""
            self.schemas.link_refs(self.tables)

        def _link_current(self, db):
            """Link augment objects to current catalog objects"""
            self.current = db
            self.schemas.link_current(db.schemas)
            self.tables.link_current(db.tables)

        def add_func(self, schema, function):
            """Add a function to a schema if not already present

            :param schema: schema name
            :param function: the possibly new function
            """
            if schema in self.schemas:
                self.schemas[schema].add_func(function)
            elif schema in self.current.schemas:
                sch = self.current.schemas[schema]
                if not hasattr(sch, 'functions'):
                    sch.functions = {}
                if function.name not in sch.functions:
                    sch.functions.update({function.name: function})

        def add_lang(self, lang):
            """Add a language if not already present

            :param lang: the possibly new language
            """
            if lang not in self.current.languages:
                self.current.languages[lang] = Language(name=lang)

    def from_augmap(self, aug_map):
        """Populate the augment objects from the input augment map

        :param aug_map: a YAML map defining the desired augmentations

        The `adb` holder is populated by various DbAugmentDict-derived
        classes by traversing the YAML augmentation map. The objects
        in the dictionary are then linked to related objects, e.g.,
        tables are linked to the schemas they belong.
        """
        self.adb = self.AugDicts()
        aug_schemas = {}
        for key in list(aug_map.keys()):
            if key == 'augmenter':
                self._from_cfgmap(aug_map[key])
            elif key.startswith('schema '):
                aug_schemas.update({key: aug_map[key]})
            else:
                raise KeyError("Expected typed object, found '%s'" % key)
        self.adb.schemas.from_map(aug_schemas, self.adb)
        self.adb._link_refs()
        self.adb._link_current(self.db)

    def _from_cfgmap(self, cfg_map):
        """Populate configuration objects from the input configuration map

        :param cfg_map: a YAML map defining augmentation configuration

        The augmentations dictionary is populated by various
        DbAugmentDict-derived classes by traversing the YAML
        configuration map.
        """
        for key in list(cfg_map.keys()):
            if key == 'columns':
                self.adb.columns.from_map(cfg_map[key])
            elif key in ['function templates', 'function segments']:
                self.adb.funcsrcs.from_map(cfg_map[key])
            elif key == 'functions':
                self.adb.functions.from_map(cfg_map[key])
            elif key == 'triggers':
                self.adb.triggers.from_map(cfg_map[key])
            elif key == 'audit_columns':
                self.adb.auditcols.from_map(cfg_map[key])
            else:
                raise KeyError("Expected typed object, found '%s'" % key)

    def apply(self, aug_map, opts):
        """Apply augmentations to an existing database

        :param aug_map: a YAML map defining the desired augmentations

        Merges an existing database definition, as fetched from the
        catalogs, with an input YAML defining augmentations on various
        objects and an optional configuration map or the predefined
        configuration.
        """
        if not self.db:
            self.from_catalog()
        self.from_augmap(aug_map)
        for sch in self.adb.schemas:
            self.adb.schemas[sch].apply(self.adb)
        return self.to_map(opts)
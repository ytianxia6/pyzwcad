#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    pyzwcad.api
    ~~~~~~~~~~~~~~~

    Main ZwCAD automation object.

    :copyright: (c) 2012 by Roman Haritonov.
    :license: BSD, see LICENSE.txt for more details.
"""

__all__ = ['ZwCAD', 'ZCAD']

import logging
import comtypes
import glob
import os
try:
    import comtypes.client
    # generate modules for work with ZCAD constants
    for pattern in ("zwcad*.tlb",):
        pattern = os.path.join(
            r"C:\Program Files\Common Files\ZWSoft Shared",
            pattern
        )
        tlib = glob.glob(pattern)[0]
        comtypes.client.GetModule(tlib)
    import comtypes.gen.ZWCAD as ZCAD
except Exception:
    # we are under readthedocs.org and need to mock this
    ZCAD = None


import pyzwcad.types
from pyzwcad.compat import basestring, xrange

logger = logging.getLogger(__name__)


class ZwCAD(object):
    """Main ZwCAD Automation object
    """

    def __init__(self, create_if_not_exists=False, visible=True):
        """
        :param create_if_not_exists: if ZwCAD doesn't run, then
                                     new instanse will be crated
        :param visible: new ZwCAD instance will be visible if True (default)
        """
        self._create_if_not_exists = create_if_not_exists
        self._visible = visible
        self._app = None

    @property
    def app(self):
        """Returns active :class:`ZwCAD.Application`

        if :class:`ZwCAD` was created with :data:`create_if_not_exists=True`,
        it will create :class:`ZwCAD.Application` if there is no active one
        """
        if self._app is None:
            try:
                self._app = comtypes.client.GetActiveObject('ZWCAD.Application', dynamic=True)
            except WindowsError:
                if not self._create_if_not_exists:
                    raise
                self._app = comtypes.client.CreateObject('ZWCAD.Application', dynamic=True)
                self._app.Visible = self._visible
        return self._app

    @property
    def doc(self):
        """ Returns `ActiveDocument` of current :attr:`Application`"""
        return self.app.ActiveDocument

    #: Same as :attr:`doc`
    ActiveDocument = doc

    #: Same as :attr:`app`
    Application = app

    @property
    def model(self):
        """ `ModelSpace` from active document """
        return self.doc.ModelSpace

    def iter_layouts(self, doc=None, skip_model=True):
        """Iterate layouts from *doc*

        :param doc: document to iterate layouts from if `doc=None` (default), :attr:`ActiveDocument` is used
        :param skip_model: don't include :class:`ModelSpace` if `True`
        """
        if doc is None:
            doc = self.doc
        for layout in sorted(doc.Layouts, key=lambda x: x.TabOrder):
            if skip_model and not layout.TabOrder:
                continue
            yield layout

    def iter_objects(self, object_name_or_list=None, block=None,
                     limit=None, dont_cast=False):
        """Iterate objects from `block`

        :param object_name_or_list: part of object type name, or list of it
        :param block: ZwCAD block, default - :class:`ActiveDocument.ActiveLayout.Block`
        :param limit: max number of objects to return, default infinite
        :param dont_cast: don't retrieve best interface for object, may speedup
                          iteration. Returned objects should be casted by caller
        """
        if block is None:
            block = self.doc.ActiveLayout.Block
        object_names = object_name_or_list
        if object_names:
            if isinstance(object_names, basestring):
                object_names = [object_names]
            object_names = [n.lower() for n in object_names]

        count = block.Count
        for i in xrange(count):
            item = block.Item(i)  # it's faster than `for item in block`
            if limit and i >= limit:
                return
            if object_names:
                object_name = item.ObjectName.lower()
                if not any(possible_name in object_name for possible_name in object_names):
                    continue
            if not dont_cast:
                item = self.best_interface(item)
            yield item

    def iter_objects_fast(self, object_name_or_list=None, container=None, limit=None):
        """Shortcut for `iter_objects(dont_cast=True)`

        Shouldn't be used in normal situations
        """
        return self.iter_objects(object_name_or_list, container, limit, dont_cast=True)

    def find_one(self, object_name_or_list, container=None, predicate=None):
        """Returns first occurance of object which match `predicate`

        :param object_name_or_list: like in :meth:`iter_objects`
        :param container: like in :meth:`iter_objects`
        :param predicate: callable, which accepts object as argument
                          and returns `True` or `False`
        :returns: Object if found, else `None`
        """
        if predicate is None:
            predicate = bool
        for obj in self.iter_objects(object_name_or_list, container):
            if predicate(obj):
                return obj
        return None

    def best_interface(self, obj):
        """ Retrieve best interface for object """
        return comtypes.client.GetBestInterface(obj)

    def prompt(self, text):
        """ Prints text in console and in `ZwCAD` prompt
        """
        print(text)
        self.doc.Utility.Prompt(u"%s\n" % text)

    def get_selection(self, text="Select objects"):
        """ Asks user to select objects

        :param text: prompt for selection
        """
        self.prompt(text)
        try:
            self.doc.SelectionSets.Item("SS1").Delete()
        except Exception:
            logger.debug('Delete selection failed')

        selection = self.doc.SelectionSets.Add('SS1')
        selection.SelectOnScreen()
        return selection

    #: shortcut for :func:`pyzwcad.types.aDouble`
    aDouble = staticmethod(pyzwcad.types.aDouble)
    #: shortcut for :func:`pyzwcad.types.aInt`
    aInt = staticmethod(pyzwcad.types.aInt)
    #: shortcut for :func:`pyzwcad.types.aShort`
    aShort = staticmethod(pyzwcad.types.aShort)



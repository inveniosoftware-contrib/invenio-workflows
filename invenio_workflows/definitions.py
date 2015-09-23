# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2014, 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Contains basic workflow types for use in workflow definitions."""


class WorkflowMissing(object):

    """Placeholder workflow definition."""

    workflow = [lambda obj, eng: None]


class WorkflowBase(object):

    """Base class for workflow definition.

    Interface to define which functions should be imperatively implemented.

    All workflows intended to work well with Holding Pen should inherit from
    this class.
    """

    @staticmethod
    def get_title(bwo, **kwargs):
        """Return the value to put in the title column of HoldingPen."""
        return "No title"

    @staticmethod
    def get_description(bwo, **kwargs):
        """Return the value to put in the title  column of HoldingPen."""
        return "No description"

    @staticmethod
    def get_additional(bwo, **kwargs):
        """Return the value to put in the additional column of HoldingPen."""
        return ""

    @staticmethod
    def formatter(obj, **kwargs):
        """Format the object."""
        return "No data"

    @staticmethod
    def get_sort_data(obj, **kwargs):
        """Return a dictionary useful for sorting in Holding Pen."""
        return {}

"""
MIT License

Copyright (c) 2023 groggyegg

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from json import dumps, loads
from os import makedirs
from os.path import exists, join

from peewee import CharField, DateTimeField, Model, SmallIntegerField, SQL, SqliteDatabase
from xbmcext import ListItem, getAddonProfilePath, getAddonPath, getLocalizedString

from request import Request

if __name__ == '__main__':
    from xbmcgui import ListItem


class JSONField(CharField):
    def db_value(self, value):
        return value if isinstance(value, str) else dumps(value, ensure_ascii=False)

    def python_value(self, value):
        return loads(value)


class ExternalDatabase(object):
    profile_path = getAddonProfilePath()
    connection = SqliteDatabase(join(profile_path, 'duboku.db'))

    @classmethod
    def close(cls):
        cls.connection.close()

    @classmethod
    def connect(cls):
        if not exists(cls.profile_path):
            makedirs(cls.profile_path)

        cls.connection.connect(True)

    @classmethod
    def create(cls):
        cls.connection.create_tables([RecentDrama, RecentFilter])
        cls.connection.commit()


class InternalDatabase(object):
    addon_path = getAddonPath()
    connection = SqliteDatabase(join(addon_path if addon_path else '..', 'resources/data/duboku.db'))

    @classmethod
    def close(cls):
        if cls.connection:
            cls.connection.close()

    @classmethod
    def connect(cls):
        cls.connection.connect(True)

    @classmethod
    def create(cls):
        cls.connection.create_tables([Drama])
        paths = {drama.path for drama in Drama.select()}

        for shows in [iter(Request.vodshow('/www.duboku.tv/vodshow/2--------{}---.html'.format(page)) for page in range(1, 51)),
                      iter(Request.vodshow('/www.duboku.tv/vodshow/1--------{}---.html'.format(page)) for page in range(1, 2)),
                      iter(Request.vodshow('/www.duboku.tv/vodshow/3--------{}---.html'.format(page)) for page in range(1, 5)),
                      iter(Request.vodshow('/www.duboku.tv/vodshow/4--------{}---.html'.format(page)) for page in range(1, 6))]:
            for show, _ in shows:
                for path in show:
                    if path not in paths:
                        paths.add(path)
                        try:
                            Drama.create(**Request.voddetail(path))
                        except AttributeError:
                            pass

        cls.connection.commit()


class ExternalModel(Model):
    class Meta:
        database = ExternalDatabase.connection


class InternalModel(Model):
    class Meta:
        database = InternalDatabase.connection


class Drama(InternalModel, ListItem):
    path = CharField(primary_key=True, constraints=[SQL('ON CONFLICT REPLACE')])
    poster = CharField()
    title = CharField()
    plot = CharField()
    category = SmallIntegerField()
    country = JSONField()
    year = SmallIntegerField()

    def __new__(cls, *args, **kwargs):
        return super(Drama, cls).__new__(cls)

    def __init__(self, *args, **kwargs):
        super(Drama, self).__init__(*args, **kwargs)
        self.setLabel(kwargs['title'] if 'title' in kwargs else '')
        self.setArt({'banner': kwargs['poster'],
                     'clearart': kwargs['poster'],
                     'fanart': kwargs['poster'],
                     'icon': kwargs['poster'],
                     'landscape': kwargs['poster'],
                     'poster': kwargs['poster'],
                     'thumb': kwargs['poster']} if 'poster' in kwargs else {})
        self.setInfo('video', {label: list(map(getLocalizedString, kwargs[label])) if label == 'country' else kwargs[label]
                               for label in ('title', 'plot', 'country', 'year') if label in kwargs})


class RecentDrama(ExternalModel):
    path = CharField(primary_key=True, constraints=[SQL('ON CONFLICT REPLACE')])
    timestamp = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])


class RecentFilter(ExternalModel, ListItem):
    path = CharField()
    title = CharField(primary_key=True, constraints=[SQL('ON CONFLICT REPLACE')])
    timestamp = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])

    def __new__(cls, *args, **kwargs):
        return super(RecentFilter, cls).__new__(cls)

    def __init__(self, *args, **kwargs):
        super(RecentFilter, self).__init__(*args, **kwargs)
        self.setLabel(kwargs['title'])
        self.setArt({'icon': 'DefaultTVShows.png'})


if __name__ == '__main__':
    try:
        InternalDatabase.connect()
        InternalDatabase.create()
    finally:
        InternalDatabase.close()

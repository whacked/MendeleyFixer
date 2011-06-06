import hashlib, os, urllib2, base64, re
import sqlite3
import sqlalchemy
from sqlalchemy import Table, MetaData, ForeignKey
from sqlalchemy import Column, CHAR, Integer, Float, String, Text, DateTime
from sqlalchemy.sql import select, and_, or_, not_
from sqlalchemy.orm import mapper, sessionmaker, relationship, backref
from sqlalchemy.ext.declarative import declarative_base


from sqlalchemy.ext.sqlsoup import SqlSoup

# get db_path from here
execfile("MendeleyConfig.py")

dsn_db = "sqlite:///%s" % db_path
db_engine = sqlalchemy.create_engine(dsn_db, echo = False)

db_sessionmaker = sessionmaker(bind = db_engine)
db_session = db_sessionmaker()

mdb = SqlSoup(dsn_db)

metadata = MetaData()
metadata.bind = db_engine

db_sessionmaker = sessionmaker(bind = db_engine)
db_session = db_sessionmaker()

#Base = declarative_base()
#Base.metadata = metadata

tbl_Documents            = Table('Documents',            metadata, autoload=True)
tbl_Files                = Table('Files',                metadata, autoload=True)
tbl_DocumentContributors = Table('DocumentContributors', metadata, autoload=True)
tbl_DocumentKeywords     = Table('DocumentKeywords',     metadata, autoload=True)
tbl_DocumentTags         = Table('DocumentTags',         metadata, autoload=True)
tbl_DocumentUrls         = Table('DocumentUrls',         metadata, autoload=True)
tbl_Folders              = Table('Folders',              metadata, autoload=True)

# association table
MDocumentFiles = Table('DocumentFiles', metadata,
                       Column('documentId', Integer, ForeignKey('Documents.id')),
                       Column('hash', CHAR(40), ForeignKey('Files.hash')))
MDocumentFolders = Table('DocumentFolders', metadata,
                         Column('documentId', Integer, ForeignKey('Documents.id')),
                         Column('folderId', Integer, ForeignKey('Folders.id')))
class MFile(object):
    def __repr__(self):
        return "[%s] %s" % (self.hash, self.localUrl)
mapper(MFile, tbl_Files, primary_key=[tbl_Files.c.hash])

class MFolder(object):
    def __repr__(self):
        return self.name
mapper(MFolder, tbl_Folders)

class MDocumentContributor(object):
    documentId = Column(Integer, ForeignKey(tbl_Documents.c.id))
    def __repr__(self):
        return "%s, %s (%s)" % (self.lastName, self.firstNames, self.contribution)
mapper(MDocumentContributor, tbl_DocumentContributors)

class MDocumentKeyword(object):
    documentId = Column(Integer, ForeignKey(tbl_Documents.c.id))
    def __repr__(self):
        return self.keyword
mapper(MDocumentKeyword, tbl_DocumentKeywords)

class MDocumentTag(object):
    documentId = Column(Integer, ForeignKey(tbl_Documents.c.id))
    def __repr__(self):
        return self.tag
mapper(MDocumentTag, tbl_DocumentTags)

class MDocumentUrl(object):
    documentId = Column(Integer, ForeignKey(tbl_Documents.c.id))
    def __repr__(self):
        return "(%s) %s" % (self.position, self.url)
mapper(MDocumentUrl, tbl_DocumentUrls)

class MDocument(object):
    def __init__(self, documentId):
        try:
            _res = db_session.query(self.__class__).filter_by(id = documentId).one()
            self.__dict__ = _res.__dict__
            for attr in ('files', 'folders', 'contributors', 'tags', 'keywords', 'urls'):
                setattr(self, attr, getattr(_res, attr))
        except sqlalchemy.orm.exc.NoResultFound, e:
            pass
mapper(MDocument, tbl_Documents,
       primary_key=[tbl_Documents.c.id],
       properties={    
        'files':        relationship(MFile, secondary=MDocumentFiles),
        'folders':      relationship(MFolder, secondary=MDocumentFolders),

        # shouldn't need backref here, not trying it out
        #'contributors': relationship(MDocumentContributor, backref="Documents"),
        'contributors': relationship(MDocumentContributor,
                                     primaryjoin = and_(tbl_Documents.c.id == tbl_DocumentContributors.c.documentId),
                                     # don't fully understand this, but without it it fails to know the direction of join
                                     foreign_keys = [tbl_DocumentContributors.c.documentId]),
        'urls':         relationship(MDocumentUrl,
                                     primaryjoin = and_(tbl_Documents.c.id == tbl_DocumentUrls.c.documentId),
                                     foreign_keys = [tbl_DocumentUrls.c.documentId]),
        'keywords':     relationship(MDocumentKeyword,
                                     primaryjoin = and_(tbl_Documents.c.id == tbl_DocumentKeywords.c.documentId),
                                     foreign_keys = [tbl_DocumentKeywords.c.documentId]),
        'tags':         relationship(MDocumentTag,
                                     primaryjoin = and_(tbl_Documents.c.id == tbl_DocumentTags.c.documentId),
                                     foreign_keys = [tbl_DocumentTags.c.documentId]),
        })

    
if __name__ == "__main__":

    z=db_session.query(MDocument).filter_by(id = 2).one()
    #sqlalchemy.orm.clear_mappers()


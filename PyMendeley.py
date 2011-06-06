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

if __name__ == "__main__":

    dsn_db = "sqlite:///%s" % db_path
    db_engine = sqlalchemy.create_engine(dsn_db, echo = True)
    
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
                             Column('folderId', Integer, ForeignKey('Folders.id')),
                             extend_existing = True)
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
                self.files = _res.files
                #self.files = _res.contributors
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
    
    
    z=db_session.query(MDocument).filter_by(id = 2).one()
    #z=db_session.query(MDocumentContributor).filter_by(id = 10).one().contribution

    #sqlalchemy.orm.clear_mappers()


# old stuff, phase out
if False:
    
    def MendeleyDB(db_path):
    
        dsn_db = "sqlite:///%s" % (db_path.startswith("/") and db_path or os.path.join(os.getcwd(), db_path))
        db_engine = sqlalchemy.create_engine(dsn_db, echo = False)
        
        metadata = MetaData()
        metadata.bind = dsn_db
        
        db_sessionmaker = sessionmaker(bind = db_engine)
        db_session = db_sessionmaker()
    
    
        mdb = SqlSoup(dsn_db)
        return mdb
    
    class File(object):
        def __init__(self, mixed, hash = None):
            if type(mixed) == tuple and len(mixed) is 2: # assume database row
                localUrl, hash = mixed
            elif hasattr(mixed, "localUrl"):
                localUrl, hash = mixed.localUrl, mixed.hash
            else: # assume filepath or file url
                localUrl = mixed
    
            localUrl = localUrl.strip().strip('\'"')
            if localUrl.startswith("file://"):
                file_path = localUrl[7:]
            else:
                if not localUrl.startswith("/"): # assume relative file path
                    localUrl = os.path.join(os.getcwd(), localUrl)
                    file_path = localUrl
                    localUrl = "file://%s" % localUrl
            if not os.path.exists(file_path):
                raise IOError("no such file")
    
            self._dc = dict(
                    localUrl = localUrl,
                    hash = hash and hash or hashlib.sha1(open(file_path, 'rb').read()).hexdigest())
    
        def __getattr__(self, attrname):
            return self._dc.get(attrname)
    
        def __str__(self):
            return "|__ FILE: %s\n   \\__at: %s" % (self._dc['hash'], self._dc['localUrl'])
    
        def __repr__(self):
            return " >> MendeleyFile: [%s] == [%s]" % (self._dc['hash'], os.path.split(self._dc['localUrl'])[1])
    
    def dupefinder(MDB):
        pass

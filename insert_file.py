import hashlib, os, urllib2, base64, re
import sqlite3

# need to insert into:
# DocumentFiles
# | documentId | hash                                     | remoteUrl | unlinked | syncedWithWeb |
# |         19 | 7f88124fff7e45215a687f2172999cd788ab4d72 |           | false    | true          |
# Files
# | hash                                     | localUrl                                                                                                                                                                                                                                                                                              |
# | 7f88124fff7e45215a687f2172999cd788ab4d72 | file:///Users/myfakename/Library/Application%20Support/Mendeley%20Desktop/Downloaded/Cloutier%20et%20al.%20-%202008%20-%20Are%20attractive%20people%20rewarding%20Sex%20differences%20in%20the%20neural%20substrates%20of%20facial%20attractiveness.pdf                                                |


DB = None
p_bdsk = re.compile("Users\\/.*?literature.*?(?:pdf|PDF|xoj)[^.]")

def make_localUrl(file_path):
    """
    
    Arguments:
    - `file_path`:
    """
    return "file://%s" % urllib2.quote(os.path.abspath(file_path.strip()))

def make_file_hash(file_path):
    return hashlib.sha1(open(file_path, 'rb').read()).hexdigest()

def get_documentId(title):
    sql_Documents = """
SELECT id FROM Documents WHERE title LIKE '%s%%'""" % (title.replace("'", "''"))
    res = DB.execute(sql_Documents).fetchone()
    if res:
        return res[0]
    else:
        return 0

def is_hash_exist(fileHash):
    if not DB: return False
    sql_File = """
SELECT COUNT(*) FROM Files WHERE hash = '%s'""" % fileHash
    res = DB.execute(sql_File)
    return res.fetchone()[0] > 0

def is_document_has_hash(documentId, fileHash):
    if not DB: return False
    sql_DocumentFiles = """
SELECT COUNT(*) FROM DocumentFiles WHERE documentId = %s AND hash = '%s'""" % (documentId, fileHash)
    res = DB.execute(sql_DocumentFiles)
    return res.fetchone()[0] > 0

def get_num_file(documentId):
    if type(documentId) == str:
        raise Exception("needs to be int")
    if not DB: return False
    sql_DocumentFiles = """
SELECT COUNT(*) FROM DocumentFiles WHERE documentId = %s""" % (documentId)
    res = DB.execute(sql_DocumentFiles)
    return res.fetchone()[0] > 0

def insert_into_db(title, file_path):
    documentId = get_documentId(title)
    if not documentId:
        raise Exception("did not find the document: [%s]" % title)
    if not os.path.exists(file_path):
        raise Exception("did not find the file: [%s]" % file_path)

    fileHash = make_file_hash(file_path)
    localUrl = make_localUrl(file_path)

    sql_DocumentFiles = """
INSERT INTO
DocumentFiles
(documentId, hash, remoteUrl, unlinked, syncedWithWeb)
VALUES
(        %s, '%s',        '',    0,          1)
""" % (documentId, fileHash)
    #print sql_DocumentFiles

    sql_Files = """
INSERT INTO
Files
(hash, localUrl)
VALUES
('%s',     '%s')
""" % (fileHash, localUrl)
    #print sql_Files

    res = False
    if DB:
        if not is_hash_exist(fileHash):
            DB.execute(sql_Files)
        DB.execute(sql_DocumentFiles)
        res = DB.commit()
    return res

def cleanline(line):
    return line.split('=', 1)[1].strip().strip('{},')

def parseBdsk(bdsk_hash):
    decoded = base64.b64decode(bdsk_hash)
    ls_match = p_bdsk.findall(decoded)
    if ls_match:
        return '/' + ls_match[0]
    else:
        return ''

if __name__ == "__main__":
    PATH_TO_BIBDESK_BIB = "/Users/myfakename/literature/_bibdesk.bib"
    PATH_TO_MENDELEY_DB = "/Users/myfakename/Library/Application Support/Mendeley Desktop/myfakename@myfakemaildomain.myfaketld@www.mendeley.com.sqlite"

    if os.path.exists(PATH_TO_MENDELEY_DB):
        DB = sqlite3.connect(PATH_TO_MENDELEY_DB)
        print "DB IS", DB, "at", PATH_TO_MENDELEY_DB
    
    article_count = 0
    multiple_file_count = 0
    dc = {}
    title = file_path = None
    ls_file_path = []
    for line in open(PATH_TO_BIBDESK_BIB).readlines()[11:]:
        line = line.strip()
        if len(line) is 0:
            continue
        if line[0] == '@' and title:
            article_count += 1
            
            if len(ls_file_path) is 1:
                dc[title] = ls_file_path[0]
            elif len(ls_file_path) > 1:
                multiple_file_count += 1
                print " " + "_" * 79
                print "/ [[ %s ]] has %s files:" % (title, len(ls_file_path))
                print "\n".join(ls_file_path)
                print "\\" + "_" * 79
            title = file_path = None
            ls_file_path = []
        elif line.startswith("Title"):
            title = cleanline(line)
        elif line.startswith("Bdsk-File"):
            bdsk_hash = cleanline(line)
            try:
                file_path = parseBdsk(bdsk_hash)
                if file_path:
                    ls_file_path.append(file_path.strip('\x00'))
            except TypeError, e:
                print title
                print "-" * 20
                print bdsk_hash
                raise Exception("bye")
    
    
    print ""
    print article_count, "articles,", len(dc), "with files"
    print multiple_file_count, "with > 1 files"
    print ""
    
    processed_count = 0
    for title, file_path in dc.items():
        documentId = get_documentId(title)
        if not documentId:
            print "DID NOT FIND:", title
            print "    uses pdf:", file_path
            print ""
        else:
            if not os.path.exists(file_path):
                print "FILE DOES NOT EXIST:", file_path
                continue
            fileHash = make_file_hash(file_path)
            if is_document_has_hash(documentId, fileHash):
                continue
            else:
                insert_into_db(title, file_path)
                processed_count += 1
            if is_hash_exist(fileHash):
                print "EXISTS IN DB:", file_path

    print "..."
    print processed_count, "processed."
        

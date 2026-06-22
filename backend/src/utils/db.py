"""
db.py
레이어: Utils
역할: MariaDB 연결 및 공통 DB 조회·저장·트랜잭션 헬퍼 함수 모음.
"""
import mariadb
from src.utils.settings import settings

conn_params = {
  "user": settings.maria_db_user,
  "password": settings.maria_db_password,
  "host": settings.maria_db_host,
  "database" : settings.maria_db_database,
  "port" : int(settings.maria_db_port)
}

def getConn():
  '''DB 연결'''
  try:
    conn = mariadb.connect(**conn_params)
    if conn == None:
        return None
    return conn
  except mariadb.Error as e:
    print(f"접속 오류 : {e}")
    return None

def findOne(sql:str, params=None):
  '''DB에서 단일 행 조회'''
  result = None
  conn = getConn()
  if not conn:
    print("MariaDB 연결 실패 (findOne)")
    return result
  try:
    with conn.cursor(dictionary=True) as cur:
        cur.execute(sql, params)
        result = cur.fetchone()
    conn.commit()
  except mariadb.Error as e:
    print(f"MariaDB Error (findOne): {e}")
    conn.rollback()
  finally:
    conn.close()
  return result

def findAll(sql:str, params=None):
  '''DB에서 여러 행 조회'''
  result = []
  conn = getConn()
  if not conn:
    print("MariaDB 연결 실패 (findAll)")
    return result
  try:
    with conn.cursor(dictionary=True) as cur:
        cur.execute(sql, params)
        result = cur.fetchall()
    conn.commit()
  except mariadb.Error as e:
    print(f"MariaDB Error (findAll): {e}")
    conn.rollback()
  finally:
    conn.close()
  return result

def save(sql:str, params=None):
  '''DB에 단일 값 저장'''
  result = False
  conn = getConn()
  if not conn:
    print("MariaDB 연결 실패 (save)")
    return result
  try:
    with conn.cursor(dictionary=True) as cur:
        cur.execute(sql, params)
    conn.commit()
    result = True
  except mariadb.Error as e:
    print(f"MariaDB Error (save): {e}")
    conn.rollback()
  finally:
    conn.close()
  return result

# params: [(v1, v2), (v3, v4), ...] 형태의 리스트
def saveMany(sql:str, params=None):
  """DB에 여러 값 한번에 저장"""
  result = False
  conn = getConn()
  if not conn:
    print("MariaDB 연결 실패 (saveMany)")
    return result
  try:
    with conn.cursor(dictionary=True) as cur:
        cur.executemany(sql, params)
    conn.commit()
    result = True
  except mariadb.Error as e:
    print(f"MariaDB Error (saveMany): {e}")
    conn.rollback()
  finally:
    conn.close()
  return result

def addKey(sql:str, params=None):
  """DB에 직전에 생성한 키값 불러오기"""
  result = [False, 0]
  conn = getConn()
  if not conn:
    print("MariaDB 연결 실패 (addKey)")
    return result
  try:
    with conn.cursor(dictionary=True) as cur:
        cur.execute(sql, params)
        cur.execute("SELECT LAST_INSERT_ID() as id")
        data = cur.fetchone()
    conn.commit()
    result[0] = True
    if data:
        result[1] = data["id"]
  except mariadb.Error as e:
    print(f"MariaDB Error (addKey): {e}")
    conn.rollback()
  finally:
    conn.close()
  return result

def exists(sql:str, params=None):
    '''DB에서 데이터 존재 여부 체크'''
    result = False
    conn = getConn()
    if not conn:
        print("MariaDB 연결 실패 (exists)")
        return result
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            count = list(row.values())[0] if row else 0
            result = True if count > 0 else False
        conn.commit()
    except mariadb.Error as e:
        print(f"MariaDB Error (exists): {e}")
        conn.rollback()
    finally:
        conn.close()
    return result

def getPageList(sql:str, parmas=None):
    '''DB에서 페이지네이션 목록 조회'''
    result = {"total": 0, "list": []}
    conn = getConn()
    if not conn:
        print("MariaDB 연결 실패 (getPageList)")
        return result
    try:
        with conn.cursor(dictionary=True) as cur:
            # 1. 전체 개수 파악 (페이지 번호 계산용)
            count_sql = f"SELECT COUNT(*) as cnt FROM ({sql}) as temp"
            cur.execute(count_sql)
            result["total"] = cur.fetchone()["cnt"]
            # 2. 실제 페이지 데이터 조회
            paging_sql = sql + " LIMIT ? OFFSET ?"
            cur.execute(paging_sql, parmas)
            result["list"] = cur.fetchall()
        conn.commit()
    except mariadb.Error as e:
        print(f"MariaDB Error (getPageList): {e}")
        conn.rollback()
    finally:
        conn.close()
    return result
# limit = 보여줄 개수, offset = 건너뛸 개수


def executeTransaction(queries: list):
    """
    여러 SQL 문을 하나의 트랜잭션으로 처리 (All or Nothing)
    queries: [(sql1, params1), (sql2, params2), ...] 형식의 리스트
    """
    result = False
    conn = getConn()
    if not conn:
        return False

    try:
        with conn.cursor(dictionary=True) as cur:
            for sql, params in queries:
                cur.execute(sql, params)
        conn.commit()
        result = True
    except mariadb.Error as e:
        print(f"MariaDB Transaction Error : {e}")
        conn.rollback()
        result = False
    finally:
        conn.close()

    return result

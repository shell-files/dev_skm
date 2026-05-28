import mariadb
from src.utils.settings import settings

# ------------------
# DB 연결
# ------------------

# env 관리
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

# --------------------------
# 하나만 불러오기
# --------------------------
def findOne(sql:str, params=None):
  '''DB에서 단일 행 조회'''
  result = None
  try:
    with getConn() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            result = cur.fetchone()
  except mariadb.Error as e:
    print(f"MariaDB Error : {e}")
  return result

# --------------------------
# 모두 불러오기
# --------------------------
def findAll(sql:str, params=None):
  '''DB에서 여러 행 조회'''
  result = []
  try:
     with getConn() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            result = cur.fetchall()
  except mariadb.Error as e:
    print(f"MariaDB Error : {e}")
  return result

# --------------------------
# DB에 저장하기
# --------------------------
def save(sql:str, params=None):
  '''DB에 단일 값 저장'''
  result = False
  try:
     with getConn() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            conn.commit()
            result = True
  except mariadb.Error as e:
    print(f"MariaDB Error : {e}")
  return result

# --------------------------
# 여러 값 저장하기
# --------------------------
def saveMany(sql:str, params=None):
  """DB에 여러 값 한번에 저장"""
  result = False
  try:
     with getConn() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.executemany(sql, params)
            conn.commit()
            result = True
  except mariadb.Error as e:
    print(f"MariaDB Error : {e}")
  return result

# --------------------------
# 직전에 넣은 키값 불러오기
# --------------------------
def addKey(sql:str, params=None):
  """DB에 직전에 생성한 키값 불러오기"""
  result = [False, 0]
  try:
    with getConn() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            sql2 = "SELECT LAST_INSERT_ID() as id"
            cur.execute(sql2)
            data = cur.fetchone()  
            conn.commit()
            result[0] = True
            if data:
                result[1] = data["id"]
  except mariadb.Error as e:
    print(f"MariaDB Error : {e}")
  return result

# --------------------------
# 데이터 존재 여부 확인
# --------------------------
def exists(sql:str, params=None):
    '''DB에서 데이터 존재 여부 체크'''
    result = False
    try:
         with getConn() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(sql, params)
                # 결과가 0보다 크면 존재하는 것
                row = cur.fetchone()
                count = list(row.values())[0] if row else 0
                result = True if count > 0 else False
    except mariadb.Error as e:
        print(f"MariaDB Error : {e}")
    return result

# --------------------------
# 페이지네이션 목록
# --------------------------
def getPageList(sql:str, parmas=None):
    '''DB에서 페이지네이션 목록 조회'''
    result = {"total": 0, "list": []}
    try:
        with getConn() as conn:
            with conn.cursor(dictionary=True) as cur:
                # 1. 전체 개수 파악 (페이지 번호 계산용)
                count_sql = f"SELECT COUNT(*) as cnt FROM ({sql}) as temp"
                cur.execute(count_sql)
                result["total"] = cur.fetchone()["cnt"]
                # 2. 실제 페이지 데이터 조회
                paging_sql = sql + " LIMIT ? OFFSET ?"
                cur.execute(paging_sql, parmas)
                result["list"] = cur.fetchall()
    except mariadb.Error as e:
        print(f"MariaDB Error : {e}")
    return result
# limit = 보여줄 개수, offset = 건너뛸 개수



# --------------------------
# 여러 SQL 문을 하나의 트랜잭션으로 처리
# --------------------------
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
        # 트랜잭션 시작 (mariadb 커넥션은 기본적으로 autocommit=False 상태가 많지만 명시적 처리)
        with conn.cursor(dictionary=True) as cur:
            for sql, params in queries:
                cur.execute(sql, params)
            
            # 모든 쿼리가 성공적으로 실행되면 커밋
            conn.commit()
            result = True
    except mariadb.Error as e:
        # 하나라도 실패하면 전체 취소
        print(f"MariaDB Transaction Error : {e}")
        conn.rollback()
        result = False
    finally:
        conn.close()
        
    return result
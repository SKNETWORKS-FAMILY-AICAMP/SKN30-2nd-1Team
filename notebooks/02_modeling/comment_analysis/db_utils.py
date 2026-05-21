"""
db_utils.py
-----------
Jupyter Notebook / Colab에서 MySQL 또는 MariaDB 데이터를 읽어오기 위한 유틸리티입니다.

설치:
    pip install pymysql pandas sqlalchemy python-dotenv

필요한 .env 예시:
    DB_HOST=192.168.0.10
    DB_PORT=3306
    DB_USER=myuser
    DB_PASSWORD=mypassword
    DB_NAME=mydb
    DB_CHARSET=utf8mb4
"""

import os
from typing import Optional, Union, Dict, Tuple, Any

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine


load_dotenv()


DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "charset": os.getenv("DB_CHARSET", "utf8mb4"),
}


def _validate_config() -> None:
    """필수 DB 접속 정보가 .env에 들어있는지 확인합니다."""
    required_keys = ["host", "user", "password", "database"]

    missing = [
        key for key in required_keys
        if DB_CONFIG.get(key) in (None, "")
    ]

    if missing:
        raise ValueError(
            "DB 접속 정보가 부족합니다. .env 파일에서 다음 값을 확인하세요: "
            + ", ".join(missing)
        )


def get_engine() -> Engine:
    """
    SQLAlchemy 엔진 객체를 생성합니다.

    Returns
    -------
    sqlalchemy.engine.Engine
        pandas.read_sql()에서 사용할 DB 연결 엔진
    """
    _validate_config()

    url = URL.create(
        drivername="mysql+pymysql",
        username=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        database=DB_CONFIG["database"],
        query={"charset": DB_CONFIG["charset"]},
    )

    return create_engine(url, pool_pre_ping=True)


def test_connection() -> None:
    """
    DB 연결이 정상인지 확인합니다.

    사용 예시
    -------
    from db_utils import test_connection
    test_connection()
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        print("DB 연결 성공")
        print(f"host     : {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        print(f"database : {DB_CONFIG['database']}")

    except Exception as e:
        print(f"DB 연결 실패: {e}")


def run_query(
    sql: str,
    params: Optional[Union[Dict[str, Any], Tuple[Any, ...]]] = None,
    display: bool = True,
) -> pd.DataFrame:
    """
    SELECT 쿼리를 실행하고 결과를 pandas DataFrame으로 반환합니다.

    Parameters
    ----------
    sql : str
        실행할 SELECT SQL 문
    params : dict 또는 tuple, optional
        SQL 파라미터 바인딩 값
    display : bool, default=True
        True이면 Jupyter / Colab 화면에 DataFrame을 바로 출력합니다.

    Returns
    -------
    pandas.DataFrame
        SQL 실행 결과

    사용 예시
    -------
    df = run_query("SELECT * FROM comments LIMIT 10", display=False)

    df = run_query(
        "SELECT * FROM comments WHERE video_id = %(video_id)s",
        params={"video_id": "abc123"},
        display=False
    )
    """
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("sql에는 비어 있지 않은 SQL 문자열을 입력해야 합니다.")

    engine = get_engine()

    df = pd.read_sql(
        sql=text(sql),
        con=engine,
        params=params,
    )

    if display:
        try:
            from IPython.display import display as ipy_display
            ipy_display(df)
        except ImportError:
            print(df)

    return df
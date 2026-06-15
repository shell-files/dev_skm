from airflow import DAG
from datetime import datetime, timedelta
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import PythonOperator
from jobs.step00 import step00
from jobs.step01 import step01
from jobs.step02 import step02
from jobs.step03 import step03
from jobs.step04 import step04
from jobs.step05 import step05
from jobs.step06 import step06
from jobs.step07 import step07

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2026, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


with DAG(
    dag_id='app01_dag',
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False
) as app01_dag:

    start = EmptyOperator(task_id='start')
    end = EmptyOperator(task_id='end')

    # task_clean = PythonOperator(
    #     task_id='task_clean',
    #     python_callable=step00
    # )

    # task_impacton_crawler = PythonOperator(
    #     task_id='task_impacton_crawler',
    #     python_callable=step01
    # )  # 18 page

    # task_esgeconomy_crawler = PythonOperator(
    #     task_id='task_esgeconomy_crawler',
    #     python_callable=step02
    # )  # 528 page

    # task_merge = PythonOperator(
    #     task_id='task_merge',
    #     python_callable=step03
    # )

    task_rag = PythonOperator(
        task_id='task_rag',
        python_callable=step04
    )

    task_embedding = PythonOperator(
        task_id='task_embedding',
        python_callable=step05
    )

    task_similarity = PythonOperator(
        task_id='task_similarity',
        python_callable=step06
    )

    task_save_vector = PythonOperator(
        task_id='task_save_vector',
        python_callable=step07
    )

    (
        start
        # >> task_clean >> [task_impacton_crawler, task_esgeconomy_crawler] >> task_merge
        >> task_rag
        >> task_embedding
        >> task_similarity
        >> task_save_vector
        >> end
    )

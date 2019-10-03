from google.cloud import bigquery
from google.oauth2 import service_account


class bigquery_handler(object):

    def __init__(self, q_base=None, location="US"):
        self.q_base = q_base
        self.location = location


        self.credentials = service_account.Credentials.from_service_account_file(
            '../info/log_queries.json',
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )

        self.client = bigquery.Client(credentials=self.credentials,
            project=self.credentials.project_id)

    def run_query(self, how='inserts'):
        
        self.query_job = self.client.query(self.q_base, location=self.location)
        
        if how == 'inserts':
            self.query_job_result = self.query_job.result()
            return self.query_job_result

        if how == 'selects':
            return self.query_job.to_dataframe()






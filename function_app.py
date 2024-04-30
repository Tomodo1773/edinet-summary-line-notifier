import logging
import azure.functions as func
from functions.finance_summary import finance_summary

app = func.FunctionApp()

@app.schedule(schedule="0 0 20 * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False)
def notify_finance_summary(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function executed.')
    finance_summary()

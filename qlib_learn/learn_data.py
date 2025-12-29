
import qlib
from qlib.data import D
from qlib.data.filter import NameDFilter

def learn_data():
    raise NotImplementedError("learn_data is not implemented")

def load_calendar():
    
    my_calendar = D.calendar(start_time="2020-01-01", end_time="2020-01-31")
    print("calendar:",my_calendar)
    return my_calendar

def load_instruments():
    nameDFilter = NameDFilter(name_rule_re='SH[0-9]{4}55')
    # filter_pipe 可以为空，为空时表示不进行过滤
    my_instruments = D.instruments(market="csi300", filter_pipe=[nameDFilter])
    print("instruments:",my_instruments)
    instrument_list = D.list_instruments(instruments=my_instruments, start_time="2020-01-01", end_time="2020-01-31")
    print("instrument_list:",instrument_list)

def load_features():
    instruments = ['SH600000']
    fields = ['$close', '$volume', 'Ref($close, 1)', 'Mean($close, 3)', '$high-$low']
    feature_list = D.features(instruments=instruments, fields=fields, start_time="2020-01-01", end_time="2020-01-10")
    print("feature_list:",feature_list)

if __name__ == "__main__":
    qlib.init(provider_uri="./qlib_data/cn_data")

    load_calendar()
    load_instruments()
    load_features()
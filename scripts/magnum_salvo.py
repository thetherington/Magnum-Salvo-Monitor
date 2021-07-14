import datetime
import json
import re
import time
import urllib.parse

import requests


class salvo_mon:
    def __init__(self, **kwargs):

        self.verbose = None
        self.insite = None
        self.frequency = "5m"
        self.message_id_number = int(time.time())
        self.room_list = []

        for key, value in kwargs.items():

            if "insite" in key and value:

                self.insite = value

                self.url = "http://%s:9200/%s,%s/_search/" % (
                    self.insite,
                    urllib.parse.quote(
                        "<log-syslog-informational-{now/d}>,<log-syslog-{now/d}>",
                        safe="",
                    ),
                    urllib.parse.quote(
                        "<log-syslog-informational-{now/d-1d}>,<log-syslog-{now/d-1d}>",
                        safe="",
                    ),
                )

            if "frequency" in key and value:
                self.frequency = value

            if key == "annotate":

                exec("from {} import {}".format(value["module"], value["dict"]), globals())

                self.room_list = eval(value["dict"] + "()")

            if "annotate_db" in key:
                self.room_list = value

        self.query = {
            "size": 10000,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "bool": {
                                "filter": [
                                    {
                                        "bool": {
                                            "should": [{"query_string": {"fields": ["process.name"], "query": "triton*"}}],
                                            "minimum_should_match": 1,
                                        }
                                    },
                                    {
                                        "bool": {
                                            "filter": [
                                                {
                                                    "bool": {
                                                        "should": [{"match": {"log.syslog.message": "salvo"}}],
                                                        "minimum_should_match": 1,
                                                    }
                                                },
                                                {
                                                    "bool": {
                                                        "should": [
                                                            {
                                                                "bool": {
                                                                    "should": [{"match": {"log.syslog.message": "successful"}}],
                                                                    "minimum_should_match": 1,
                                                                }
                                                            },
                                                            {
                                                                "bool": {
                                                                    "should": [{"match": {"log.syslog.message": "failed"}}],
                                                                    "minimum_should_match": 1,
                                                                }
                                                            },
                                                        ],
                                                        "minimum_should_match": 1,
                                                    }
                                                },
                                            ]
                                        }
                                    },
                                ]
                            }
                        },
                        {
                            "range": {
                                "@timestamp": {
                                    "from": "now-{}".format(self.frequency),
                                    "to": "now",
                                }
                            }
                        },
                    ]
                }
            },
            "sort": [{"@timestamp": {"order": "asc"}}],
        }

    def fetch(self):

        try:

            header = {"Content-Type": "application/json"}
            params = {"ignore_unavailable": "true"}

            response = requests.get(self.url, data=json.dumps(self.query), params=params, headers=header, timeout=30.0)
            response.close()

            return json.loads(response.text)

        except Exception as e:

            with open("salvo_mon", "a+") as f:
                f.write(str(datetime.datetime.now()) + " --- " + "fetch" + "\t" + str(e) + "\r\n")

            return None

    def collect(self):

        results = self.fetch()

        documents = []

        if isinstance(results, dict):

            if "hits" in results.keys():

                for hit in results["hits"]["hits"]:

                    doc = hit["_source"]

                    fields = {
                        "s_type": "salvo_monitor",
                        "s_daemon": doc["process"]["name"],
                        "s_magnum_name": doc["host"]["name"],
                        "s_magnum_ip": doc["host"]["ip"],
                        "t_time": doc["@timestamp"],
                        "s_time_display": self.parse_date(doc["@timestamp"]),
                        "l_msg_id": self.message_id,
                    }

                    for room in self.room_list:
                        if room in doc["host"]["name"]:
                            fields.update({"s_pcr": room})

                    if "Salvo successful" in doc["log"]["syslog"]["message"]:

                        fields.update({"s_result": "success"})
                        fields.update(self.parse_success(doc["log"]["syslog"]["message"]))

                        document = {
                            "fields": fields,
                            "host": doc["host"]["name"],
                            "name": "salvo",
                        }

                        documents.append(document)

                    elif "Salvo failed" in doc["log"]["syslog"]["message"]:

                        fields.update({"s_result": "failed"})
                        fields.update(self.parse_failure(doc["log"]["syslog"]["message"]))

                        document = {
                            "fields": fields,
                            "host": doc["host"]["name"],
                            "name": "salvo",
                        }

                        documents.append(document)

        return documents

    @property
    def message_id(self):

        self.message_id_number += 1

        return self.message_id_number

    def parse_date(self, date_str):

        try:

            dt = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            dt = dt - datetime.timedelta(hours=4)

            return dt.strftime("%b %d %H:%M:%S EST")

        except Exception:
            pass

    def parse_success(self, message):

        fields = {}

        for key in ["Salvo", "User", "Address"]:

            modulePattern = re.compile(key + r" \[(.*?)\]")

            matchValue = modulePattern.finditer(message)

            for match in matchValue:
                fields.update({key.lower(): match.group(1)})

        return fields

    def parse_failure(self, message):

        fields = {}

        overrides = {"Salvo": "salvo", "User": "as_errors", "Address": "user", "Error": "address"}

        for key in ["Salvo", "User", "Address", "Error"]:

            modulePattern = re.compile(key + r" \[(.*?)\]")

            matchValue = modulePattern.finditer(message)

            for match in matchValue:

                if key == "User":

                    try:

                        errors = match.group(1).replace("[", "").replace("'", "").split(", ")
                        fields.update({overrides[key]: errors, "i_num_issues": len(errors)})

                    except Exception:

                        fields.update({overrides[key].replace("as", "s"): match.group(1).replace("[", "").replace("'", "")})

                else:
                    fields.update({overrides[key]: match.group(1)})

        return fields


def main():

    params = {
        "insite": "172.16.205.77",
        "frequency": "5h",
        "annotate": {"module": "ThirtyRock_PROD_edge_def", "dict": "return_roomlist"},
    }

    collector = salvo_mon(**params)

    resp = collector.collect()
    # print(json.dumps(collector.fetch(), indent=2))
    print(json.dumps(resp, indent=2))
    print(len(resp))


if __name__ == "__main__":
    main()

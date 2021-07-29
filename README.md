# Magnum Salvo Log Collector

The purpose of this script module is to discover salvo syslog messages generated from Magnum, and then re-format the log messages into high level action logs.  This module queries the inSITE database for certain log mesages from any triton process and finds log messages about salvo's executing from a Magnum Client Host server.  

Below are the module distinct abilities and features that it provides:

1. Detects salvo execution failures.
2. Re-indexes salvo log messages into a structured field format.
3. Groups multiple Magnum systems.
4. Provides a sorting weight to each document for easier aggregation.
5. Supports a custom control room annotations definition (_if one exists_)

## Minimum Requirements:

- inSITE Version 10.3 Service Pack 6
- Python3.7 (_already installed on inSITE machine_)
- Python3 Requests library (_already installed on inSITE machine_)

## Installation:

Installation of the status monitoring module requires copying two scripts into the poller modules folder:

1. Copy __magnum_salvo.py__ script to the poller python modules folder:
   ```
    cp scripts/magnum_salvo.py /opt/evertz/insite/parasite/applications/pll-1/data/python/modules/
   ```

2. Restart the poller application

## Configuration:

To configure a poller to use the module start a new python poller configuration outlined below

1. Click the create a custom poller from the poller application settings page
2. Enter a Name, Summary and Description information
3. Enter the inSITE Server IP in the _Hosts_ tab
4. From the _Input_ tab change the _Type_ to __Python__
5. From the _Input_ tab change the _Metric Set Name_ field to __magnum__
6. From the _Input_ tab change the _Freqency_ value to __300000__ (_5 minutes_)
7. From the _Python_ tab select the _Advanced_ tab and enable the __CPython Bindings__ option
8. Select the _Script_ tab, then paste the contents of __scripts/poller_config.py__ into the script panel.

9. Locate the below section of the script and update the _insite_ parameter with the elasticsearch ip address:

   ```
            params = {
                "insite": "172.16.205.201",
   ```

10. (Optional) Locate the sections that import a custom control room definition file (_if available_) and uncomment the lines.

   ```
            # control room annotation file
            from ThirtyRock_PROD_edge_def import return_roomlist
   ```

   ```
                "annotate_db": return_roomlist(),
            }
   ```


9.  Save changes, then restart the poller program.

## Testing:

The magnum_salvo script can be ran manually from the shell using the following command

```
python magnum_salvo.py
```

```
[
  {
    "fields": {
      "t_time": "2021-07-20T12:02:25.358Z",
      "s_magnum_ip": "100.103.225.29",
      "user": "VUE",
      "s_result": "success",
      "l_msg_id": 1626787492,
      "salvo": "SDO 4E MSNBC",
      "s_type": "salvo_monitor",
      "s_daemon": "triton1",
      "s_pcr": "CR31",
      "s_magnum_name": "MAG-CR31-Y",
      "s_time_display": "Jul 20 08:02:25 EST",
      "address": "100.103.229.94"
    },
    "name": "salvo",
    "host": "MAG-CR31-Y"
  },
  {
    "fields": {
      "t_time": "2021-07-20T13:06:30.423Z",
      "s_magnum_ip": "100.103.224.25",
      "user": "VUE-100.103.229.49",
      "s_result": "failed",
      "l_msg_id": 1626787512,
      "salvo": "3VL1 TO SDO 4E GB",
      "s_type": "salvo_monitor",
      "s_daemon": "triton1",
      "as_errors": [
        "Error: Router at 100.103.233.27:4000 returned error code (.SV1,73)",
        "Error: Router at 100.103.233.27:4000 returned error code (.SV4,76)",
        "Error: Router at 100.103.233.27:4000 returned error code (.SV2,74)",
        "Error: Router at 100.103.233.27:4000 returned error code (.SV3,75)"
      ],
      "s_time_display": "Jul 20 09:06:30 EST",
      "s_magnum_name": "MAG-SHARED-X",
      "i_num_issues": 4,
      "address": "100.103.229.49"
    },
    "name": "salvo",
    "host": "MAG-SHARED-X"
  }
]
```

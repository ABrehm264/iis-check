import time
import requests
import socket

hostname = socket.gethostname()
YAML = 'C:/ProgramData/Datadog/conf.d/http_local_check.yaml'

from checks import AgentCheck
from hashlib import md5

class LocalHTTPCheck(AgentCheck):
    def check(self, instance):
        if 'host_header' not in instance:
            self.log.info("Skipping instance, no host_header found.")
            return

        # Load values from the instance config
        host_header = instance['host_header']
        url = instance['url']
        metric_name = "%s_%s" % (host_header,hostname)
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))
        status = AgentCheck.OK

        # Use a hash of the metric_name as an aggregation key
        aggregation_key = md5(metric_name).hexdigest()

        # Check the URL
        start_time = time.time()
        try:
            hh = {'host': host_header }
            r = requests.get(url, headers=hh, timeout=timeout, allow_redirects=False)
            end_time = time.time()
        except requests.exceptions.Timeout as e:
            # If there's a timeout
            status = AgentCheck.CRITICAL
            return

        if (r.status_code != 200 and r.status_code != 302 and r.status_code != 404):
            status = AgentCheck.CRITICAL

        timing = end_time - start_time
        gauge_name = "http.response_time.%s" % metric_name
        self.gauge(gauge_name, timing, tags=['http_local_check'])

        tag = ["http_local_site:%s" % metric_name]
        message_str = "LocalHTTPSite %s %s"
        status_str = {
            AgentCheck.OK: "OK",
            AgentCheck.WARNING: "WARNING",
            AgentCheck.CRITICAL: "CRITICAL"
        }

        self.service_check(
            "http_local_site.up",
            status,
            tags=tag,
            message=message_str %  (metric_name, status_str[status])
        )

    def timeout_event(self, metric_name, timeout, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'http_local_check',
            'msg_title': 'URL timeout',
            'msg_text': '%s timed out after %s seconds.' % (metric_name, timeout),
            'aggregation_key': aggregation_key
        })

    def status_code_event(self, metric_name, r, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'http_local_check',
            'msg_title': 'Invalid reponse code for %s' % metric_name,
            'msg_text': '%s returned a status of %s' % (metric_name, r.status_code),
            'aggregation_key': aggregation_key
        })

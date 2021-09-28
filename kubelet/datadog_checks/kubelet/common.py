# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.base.utils.tagging import tagger

try:
    from containers import is_excluded as c_is_excluded
except ImportError:
    # Don't fail on < 6.2
    import logging

    log = logging.getLogger(__name__)
    log.info('Agent does not provide filtering logic, disabling container filtering')

    def c_is_excluded(name, image, namespace=""):
        return False


SOURCE_TYPE = 'kubelet'

CADVISOR_DEFAULT_PORT = 0


def tags_for_pod(pod_id, cardinality):
    """
    Queries the tagger for a given pod uid
    :return: string array, empty if pod not found
    """
    return tagger.tag('kubernetes_pod_uid://%s' % pod_id, cardinality) or []


def tags_for_docker(cid, cardinality, with_prefix=False):
    """
    Queries the tagger for a given container id.
    If with_prefix=true, method won't add `container_id://` to `cid`
    :return: string array, empty if container not found
    """
    if not with_prefix:
        cid = 'container_id://%s' % cid
    return tagger.tag(cid, cardinality) or []


def get_pod_by_uid(uid, podlist):
    """
    Searches for a pod uid in the podlist and returns the pod if found
    :param uid: pod uid
    :param podlist: podlist dict object
    :return: pod dict object if found, None if not found
    """
    for pod in podlist.get("items", []):
        try:
            if pod["metadata"]["uid"] == uid:
                return pod
        except KeyError:
            continue
    return None


def is_static_pending_pod(pod):
    """
    Return if the pod is a static pending pod
    See https://github.com/kubernetes/kubernetes/pull/57106
    :param pod: dict
    :return: bool
    """
    try:
        if pod["metadata"]["annotations"]["kubernetes.io/config.source"] == "api":
            return False

        pod_status = pod["status"]
        if pod_status["phase"] != "Pending":
            return False

        return "containerStatuses" not in pod_status
    except KeyError:
        return False


def replace_container_rt_prefix(cid):
    """
    Return the container ID after replacing the container runtime
    prefix with container_id://.
    Return the string unchanged if no such prefix is found.
    Eg: replace_container_rt_prefix('docker://deadbeef') --> 'container_id://deadbeef'
    :param cid: string
    :return: string
    """
    if cid and '://' in cid:
        return '://'.join(['container_id', cid.split('://')[1]])
    return cid


class PodListUtils(object):
    """
    Queries the podlist and the agent6's filtering logic to determine whether to
    send metrics for a given container.
    Results and podlist are cached between calls to avoid the repeated python-go switching
    cost (filter called once per prometheus metric), hence the PodListUtils object MUST
    be re-created at every check run.

    Containers that are part of a static pod are not filtered, as we cannot currently
    reliably determine their image name to pass to the filtering logic.
    """

    def __init__(self, podlist):
        self.containers = {}
        self.pods = {}
        self.static_pod_uids = set()
        self.cache = {}
        self.pod_uid_by_name_tuple = {}
        self.container_id_by_name_tuple = {}
        self.container_id_to_namespace = {}

        pods = podlist.get('items', [])

        for pod in pods:
            metadata = pod.get("metadata", {})
            uid = metadata.get("uid")
            namespace = metadata.get("namespace")
            pod_name = metadata.get("name")
            self.pod_uid_by_name_tuple[(namespace, pod_name)] = uid
            self.pods[uid] = pod

            # FIXME we are forced to do that because the Kubelet PodList isn't updated
            # for static pods, see https://github.com/kubernetes/kubernetes/pull/59948
            if is_static_pending_pod(pod):
                self.static_pod_uids.add(uid)

            for ctr in pod.get('status', {}).get('containerStatuses', []):
                cid = ctr.get('containerID')
                if not cid:
                    continue
                self.containers[cid] = ctr
                self.container_id_by_name_tuple[(namespace, pod_name, ctr.get('name'))] = cid
                self.container_id_to_namespace[cid] = namespace

    def get_uid_by_name_tuple(self, name_tuple):
        """
        Get the pod uid from the tuple namespace and name

        :param name_tuple: (pod_namespace, pod_name)
        :return: str or None
        """
        return self.pod_uid_by_name_tuple.get(name_tuple, None)

    def get_cid_by_name_tuple(self, name_tuple):
        """
        Get the container id (with runtime scheme) from the tuple namespace,
        name and container name

        :param name_tuple: (pod_namespace, pod_name, container_name)
        :return: str or None
        """
        return self.container_id_by_name_tuple.get(name_tuple, None)

    def is_excluded(self, cid, pod_uid=None):
        """
        Queries the agent6 container filter interface. It retrieves container
        name + image from the podlist, so static pod filtering is not supported.

        Result is cached between calls to avoid the python-go switching cost for
        prometheus metrics (will be called once per metric)
        :param cid: container id
        :param pod_uid: pod UID for static pod detection
        :return: bool
        """
        if not cid:
            return True

        if cid in self.cache:
            return self.cache[cid]

        if pod_uid and pod_uid in self.static_pod_uids:
            self.cache[cid] = False
            return False

        if cid not in self.containers:
            # Filter out metrics not coming from a container (system slices)
            self.cache[cid] = True
            return True
        ctr = self.containers[cid]
        if not ("name" in ctr and "image" in ctr):
            # Filter out invalid containers
            self.cache[cid] = True
            return True

        excluded = c_is_excluded(ctr.get("name"), ctr.get("image"), self.container_id_to_namespace.get(cid, ""))
        self.cache[cid] = excluded
        return excluded

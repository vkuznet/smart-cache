import hashlib
import io
import json
from os import path

import requests
import urllib3

from yaspin import yaspin


class HTTPFS(object):

    """Hadoop httpfs interface."""

    def __init__(self, url, http_user=None, http_password=None, verify=False, allow_redirects=False, hadoop_user='root', disable_warnings=True):
        """Init function httpfs interface.

        Args:
            http_user (str): http username
            http_password (str): http password
            verify (bool): verify the ssl certificate
            allow_redirects (bool): allow request redirect
            hadoop_user (str): hdfs user (default: root)

        Returns:
            HTTPFS: the instance of this object

        """
        self._server_url = url
        self._http_user = http_user
        self._http_password = http_password
        self._verify = verify
        self._allow_redirects = allow_redirects
        self._api_url = "/webhdfs/v1"
        self._hadoop_user = hadoop_user
        self.__disable_warnings = disable_warnings

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    def mkdirs(self, hdfs_path):
        """Make directories in hadoop with httpfs.

        Args:
            hdfs_path (str): path to create

        Returns:
            bool: true if everything went ok

        """
        if self.__disable_warnings:
            urllib3.disable_warnings()

        res = requests.put(
            "{}{}{}".format(
                self._server_url,
                self._api_url,
                hdfs_path
            ),
            params={
                'op': "MKDIRS",
                'user.name': self._hadoop_user
            },
            auth=(self._http_user, self._http_password),
            verify=self._verify,
            allow_redirects=self._allow_redirects
        )
        if res.status_code != 200:
            raise Exception("Error on make folders:\n{}".format(res.text))
        return res.json()['boolean']

    def liststatus(self, hdfs_path, print_list=False):
        """List a directory in hadoop with httpfs.

        Args:
            hdfs_path (str): path to create
            print_list (bool): if is necessary to print the list on stdout

        Returns:
            generator: (type, pathSuffix, full_hdfs_path) 

        """
        if self.__disable_warnings:
            urllib3.disable_warnings()

        res = requests.get(
            "{}{}{}".format(
                self._server_url,
                self._api_url,
                hdfs_path
            ),
            params={
                'op': "LISTSTATUS",
                'user.name': self._hadoop_user
            },
            auth=(self._http_user, self._http_password),
            verify=self._verify,
            allow_redirects=self._allow_redirects
        )
        if res.status_code != 200:
            raise Exception("Error on liststatus of folder '{}':\n{}".format(
                hdfs_path, json.dumps(res.json(), indent=2)))
        res = res.json()
        if print_list:
            print("### hdfs path: {} ###".format(hdfs_path))
            for record in res['FileStatuses']['FileStatus']:
                print("-[{}] {}".format(record['type'], record['pathSuffix']))
        # Generator
        for record in res['FileStatuses']['FileStatus']:
            yield record['type'], record['pathSuffix'], path.join(hdfs_path, record['pathSuffix'])

    def delete(self, hdfs_path, recursive=True):
        """Delete a specific path in hadoop with httpfs.

        Args:
            hdfs_path (str): path to delete

        Returns:
            bool: true if everything went ok

        """
        if self.__disable_warnings:
            urllib3.disable_warnings()

        res = requests.delete(
            "{}{}{}".format(
                self._server_url,
                self._api_url,
                hdfs_path
            ),
            params={
                'op': "DELETE",
                'user.name': self._hadoop_user,
                'recursive': recursive
            },
            auth=(self._http_user, self._http_password),
            verify=self._verify,
            allow_redirects=self._allow_redirects
        )
        if res.status_code != 200:
            raise Exception("Error on delete path '{}':\n{}".format(
                hdfs_path, json.dumps(res.json(), indent=2)))
        return res.json()['boolean']

    def open(self, hdfs_path, noredirect=True, chunk_size=256):
        """Open a file in hadoop with httpfs.

        Args:
            hdfs_path (str): path to create
            noredirect (bool): not redirect the request
            chunk_size (int): num of bytes read in a chunk

        Returns:
            io.BytesIO: the content of the file

        """
        if self.__disable_warnings:
            urllib3.disable_warnings()

        res = requests.get(
            "{}{}{}".format(
                self._server_url,
                self._api_url,
                hdfs_path
            ),
            params={
                'op': "OPEN",
                'user.name': self._hadoop_user,
                'noredirect': noredirect,
            },
            auth=(self._http_user, self._http_password),
            verify=self._verify,
            allow_redirects=self._allow_redirects,
            stream=True
        )
        if res.status_code != 200:
            raise Exception("Error on open file '{}':\n{}".format(
                hdfs_path, json.dumps(res.json(), indent=2)))

        content = io.BytesIO()
        with yaspin(text="[Opening file {}...]".format(hdfs_path)) as spinner:
            for chunk in res.iter_content(chunk_size):
                content.write(chunk)
            spinner.write("[File {} is ready...]".format(hdfs_path))
        content.seek(0)
        return content

    def create(self, hdfs_path, data, overwrite=False, noredirect=True):
        """Create a file in hadoop with httpfs.

        Args:
            hdfs_path (str): path to delete
            data (str, IOBytes): the path of the file to write into hdfs
            overwrite (bool): overwrite or not the file in hdfs
            noredirect (bool): not redirect the request

        Returns:
            bool: true if everything went ok

        """
        if self.__disable_warnings:
            urllib3.disable_warnings()

        file_url = "{}{}{}".format(
            self._server_url,
            self._api_url,
            hdfs_path
        )
        res = requests.put(
            file_url,
            params={
                'op': "CREATE",
                'user.name': self._hadoop_user,
                'noredirect': noredirect,
                'overwrite': overwrite
            },
            auth=(self._http_user, self._http_password),
            verify=self._verify,
            allow_redirects=self._allow_redirects
        )
        if res.status_code not in [200, 201, 307]:
            raise Exception("Error on create file:\n{}".format(
                json.dumps(res.json(), indent=2)))
        if isinstance(data, str) and path.isfile(data):
            with open(data, 'rb') as file_:
                res = requests.put(
                    file_url,
                    headers={
                        'content-type': "application/octet-stream"
                    },
                    params={
                        'op': "CREATE",
                        'user.name': self._hadoop_user,
                        'noredirect': noredirect,
                        'overwrite': overwrite,
                        'data': True
                    },
                    auth=(self._http_user, self._http_password),
                    verify=self._verify,
                    allow_redirects=self._allow_redirects,
                    data=file_
                )
        elif isinstance(data, io.IOBase):
            res = requests.put(
                file_url,
                headers={
                    'content-type': "application/octet-stream"
                },
                params={
                    'op': "CREATE",
                    'user.name': self._hadoop_user,
                    'noredirect': noredirect,
                    'overwrite': overwrite,
                    'data': True
                },
                auth=(self._http_user, self._http_password),
                verify=self._verify,
                allow_redirects=self._allow_redirects,
                data=data
            )
        else:
            raise Exception(
                "ERROR: You can pass a file or a byte stream, you passed '{}'".format(
                    type(data)))

        if res.status_code not in [200, 201, 307]:
            raise Exception("Error on upload file:\n{}".format(
                json.dumps(res.json(), indent=2)))
        return True


class ElasticSearchHttp(object):

    def __init__(self, url, auth):
        self.__url = url
        if self.__url[-1] != "/":
            self.__url += "/"
        self.__auth = tuple(auth.split(":")) if auth != "" else None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    @staticmethod
    def __gen_id(string):
        blake2s = hashlib.blake2s()
        blake2s.update(string.encode("utf-8"))
        return blake2s.hexdigest()

    def put(self, data):

        urllib3.disable_warnings()

        if isinstance(data, list):
            all_objects = [json.dumps(elm) for elm in data]
            all_object_ids = [
                json.dumps(
                    {"index": {"_id": self.__gen_id(elm)}}
                )
                for elm in all_objects
            ]
            data2send = zip(all_object_ids, all_objects)
            bulk = "\n".join((
                "\n".join(elms) for elms in data2send
            )) + "\n"

            res = requests.put(
                self.__url + "_bulk",
                auth=self.__auth,
                data=bulk,
                headers={'Content-Type': "application/json"},
                verify=False
            )
        else:
            json_data = json.dumps(data)
            id_data = self.__gen_id(json_data)

            res = requests.put(
                self.__url + id_data,
                auth=self.__auth,
                data=json_data,
                headers={'Content-Type': "application/json"},
                verify=False
            )

        return res

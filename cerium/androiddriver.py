# Licensed to the White Turing under one or more
# contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

'''The AndroidDriver implementation.'''


import os
import re
import tempfile

from lxml import html

from .by import By
from .elements import Elements
from .exceptions import (ApplicationsException, CharactersException,
                         DeviceConnectionException, NoSuchElementException,
                         NoSuchPackageException)
from .intent import Actions, Category
from .keys import Keys
from .service import _PATH, Service
from .utils import merge_dict


class BaseAndroidDriver(Service):
    '''Controls Android Debug Bridge and allows you to drive the android device.'''

    _element_cls = Elements
    _temp = os.path.join(tempfile.gettempdir(), 'uidump.xml')
    _nodes = None

    def view_focused_activity(self) -> str:
        '''View focused activity.'''
        output, _ = self._execute(
            '-s', self.device_sn, 'shell', 'dumpsys', 'activity', 'activities')
        return re.findall(r'mFocusedActivity: .+(com[a-zA-Z0-9\.]+/.[a-zA-Z0-9\.]+)', output)[0]

    def view_running_services(self, package: str='') -> str:
        '''View running services.'''
        output, _ = self._execute(
            '-s', self.device_sn, 'shell', 'dumpsys', 'activity', 'services', package)
        return output

    def view_package_info(self, package: str='') -> str:
        '''View package detail information.'''
        output, _ = self._execute(
            '-s', self.device_sn, 'shell', 'dumpsys', 'package', package)
        return output

    def view_current_app_behavior(self) -> str:
        '''View application behavior in the current window.'''
        output, _ = self._execute(
            '-s', self.device_sn, 'shell', 'dumpsys', 'window', 'windows')
        return re.findall(r'mCurrentFocus=.+(com[a-zA-Z0-9\.]+/.[a-zA-Z0-9\.]+)', output)[0]

    def view_surface_app_activity(self) -> str:
        '''Get package with activity of applications that are running in the foreground.'''
        output, error = self._execute(
            '-s', self.device_sn, 'shell', 'dumpsys', 'window', 'w')
        return re.findall(r"name=([a-zA-Z0-9\.]+/.[a-zA-Z0-9\.]+)", output)

    # Interact with Applications
    def _app_base_start(self, option: str, args: list or tuple) -> None:
        '''
        Args:
            option:
                -a <ACTION>
                -c <CATEGORY>
                -n <COMPONENT>
        '''
        _, error = self._execute('-s', self.device_sn,
                                 'shell', 'am', 'start', option, *args)
        if error and error.startswith('Error'):
            raise ApplicationsException(error.split(':', 1)[-1].strip())

    def app_start_action(self, *args) -> None:
        '''Start action.'''
        self._app_base_start('-a', args)

    def app_start_category(self, *args) -> None:
        '''Start category.'''
        self._app_base_start('-c', args)

    def app_start_activity(self, *args) -> None:
        '''Start activity.'''
        self._app_base_start('-n', args)

    def app_start_service(self, *args) -> None:
        '''Start a service.'''
        _, error = self._execute('-s', self.device_sn,
                                 'shell', 'am', 'startservice', *args)
        if error and error.startswith('Error'):
            raise ApplicationsException(error.split(':', 1)[-1].strip())

    def app_stop_service(self, *args) -> None:
        '''Stop a service'''
        _, error = self._execute('-s', self.device_sn, 'shell',
                                 'am', 'stopservice', *args)
        if error and error.startswith('Error'):
            raise ApplicationsException(error.split(':', 1)[-1].strip())

    def app_broadcast(self, *args) -> None:
        '''Send a broadcast.'''
        _, error = self._execute('-s', self.device_sn, 'shell',
                                 'am', 'broadcast', *args)
        if error:
            raise ApplicationsException(error.split(':', 1)[-1].strip())

    def close_app(self, package: str) -> None:
        '''Close an application.'''
        self._execute('-s', self.device_sn, 'shell',
                      'am', 'force-stop', package)

    def app_trim_memory(self, pid: int or str, level: str = 'RUNNING_LOW') -> None:
        '''Trim memory.

        Args:
            level: HIDDEN | RUNNING_MODERATE | BACKGROUNDRUNNING_LOW | \
                     MODERATE | RUNNING_CRITICAL | COMPLETE
        '''
        _, error = self._execute('-s', self.device_sn, 'shell',
                                 'am', 'send-trim-memory', str(pid), level)
        if error and error.startswith('Error'):
            raise ApplicationsException(error.split(':', 1)[-1].strip())

    def app_start_up_time(self, package: str) -> str:
        '''Get the time it took to launch your application.'''
        output, _ = self._execute(
            '-s', self.device_sn, 'shell', 'am', 'start', '-W', package)
        return re.findall('TotalTime: \d+', output)[0]

    def screencap(self, filename: _PATH='/sdcard/screencap.png') -> None:
        '''Taking a screenshot of a device display.'''
        self._execute('-s', self.device_sn, 'shell',
                      'screencap', '-p', filename)

    def pull_screencap(self, remote: _PATH = '/sdcard/screencap.png', local: _PATH = 'screencap.png') -> None:
        '''Taking a screenshot of a device display, then copy it to your computer.'''
        self.screencap(remote)
        self.pull(remote, local)

    def screencap_exec(self, filename: _PATH = 'screencap.png') -> None:
        '''Taking a screenshot of a device display, then copy it to your computer.'''
        self._execute('-s', self.device_sn, 'exec-out',
                      'screencap', '-p', '>', filename, shell=True)

    def screenrecord(self, bit_rate: int = 5000000, time_limit: int = 180, filename: _PATH = '/sdcard/demo.mp4') -> None:
        '''Recording the display of devices running Android 4.4 (API level 19) and higher.

        Args:
            bit_rate:You can increase the bit rate to improve video quality, but doing so results in larger movie files.
            time_limit: Sets the maximum recording time, in seconds, and the maximum value is 180 (3 minutes).
        '''
        self._execute('-s', self.device_sn, 'shell',
                      'screenrecord', '--bit-rate', str(bit_rate), '--time-limit', str(time_limit), filename)

    def pull_screenrecord(self, bit_rate: int = 5000000, time_limit: int = 180, remote: _PATH = '/sdcard/demo.mp4', local: _PATH = 'demo.mp4') -> None:
        '''Recording the display of devices running Android 4.4 (API level 19) and higher. Then copy it to your computer.

        Args:
            bit_rate:You can increase the bit rate to improve video quality, but doing so results in larger movie files.
            time_limit: Sets the maximum recording time, in seconds, and the maximum value is 180 (3 minutes).
        '''
        self.screenrecord(bit_rate, time_limit, filename=remote)
        self.pull(remote, local)

    def click(self, x: int, y: int) -> None:
        '''Simulate finger click.'''
        self._execute('-s', self.device_sn, 'shell',
                      'input', 'tap', str(x), str(y))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 100) -> None:
        '''Simulate finger swipe. (1000ms = 1s)'''
        self._execute('-s', self.device_sn, 'shell',
                      'input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(duration))

    def long_press(self, x: int, y: int, duration: int = 1000) -> None:
        '''Simulate finger long press somewhere. (1000ms = 1s)'''
        self._execute('-s', self.device_sn, 'shell',
                      'input', 'swipe', str(x), str(y), str(x), str(y), str(duration))

    def send_keys(self, text: str = 'cerium') -> None:
        '''Simulates typing keys.'''
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                raise CharactersException(
                    f'Text cannot contain non-English characters, such as {char!r}.')
        text = re.escape(text)
        self._execute('-s', self.device_sn, 'shell',
                      'input', 'text', text)

    def send_keyevents(self, keyevent: int) -> None:
        '''Simulates typing keyevents.'''
        self._execute('-s', self.device_sn, 'shell',
                      'input', 'keyevent', str(keyevent))

    def send_keyevents_long_press(self, keyevent: int) -> None:
        '''Simulates typing keyevents long press.'''
        self._execute('-s', self.device_sn, 'shell',
                      'input', 'keyevent', '--longpress', str(keyevent))

    def send_monkey(self, *args) -> None:
        '''Generate pseudo-random user events to simulate clicks, touches, gestures, etc.'''
        self._execute('-s', self.device_sn, 'shell', 'monkey', *args)

    def reboot(self) -> None:
        '''Reboot the device.'''
        self._execute('-s', self.device_sn, 'reboot')

    def recovery(self) -> None:
        '''Reboot to recovery mode.'''
        self._execute('-s', self.device_sn, 'reboot', 'recovery')

    def fastboot(self) -> None:
        '''Reboot to bootloader mode.'''
        self._execute('-s', self.device_sn, 'reboot', 'bootloader')

    def uidump(self, local: _PATH = None) -> None:
        '''Get the current interface layout file.'''
        local = local if local else self._temp
        self._execute('-s', self.device_sn, 'shell', 'uiautomator',
                      'dump', '--compressed', '/data/local/tmp/uidump.xml')
        self.pull('/data/local/tmp/uidump.xml', local)
        ui = html.fromstring(open(local, 'rb').read())
        self._nodes = ui.iter(tag="node")

    def find_element(self, value, by=By.ID, update=False) -> Elements:
        '''Find a element or the first element.'''
        if update or not self._nodes:
            self.uidump()
        for node in self._nodes:
            if node.attrib[by] == value:
                bounds = node.attrib['bounds']
                coord = list(map(int, re.findall(r'\d+', bounds)))
                click_point = (coord[0] + coord[2]) / \
                    2, (coord[1] + coord[3]) / 2
                return self._element_cls(self, node.attrib, by, value, coord, click_point)
        raise NoSuchElementException(f'No such element: {by}={value!r}.')

    def find_elements(self, value, by=By.ID, update=False) -> Elements:
        '''Find all elements.'''
        elements = []
        if update or not self._nodes:
            self.uidump()
        for node in nodes:
            if node.attrib[by] == value:
                bounds = node.attrib['bounds']
                coord = list(map(int, re.findall(r'\d+', bounds)))
                click_point = (coord[0] + coord[2]) / \
                    2, (coord[1] + coord[3]) / 2
                elements.append(self._element_cls(
                    self, node.attrib, by, value, coord, click_point))
        if elements:
            return elements
        raise NoSuchElementException(f'No such element: {by}={value!r}.')

    def find_element_by_id(self, id_, update=False) -> Elements:
        '''Finds an element by id.

        Args:
            id_: The id of the element to be found.
            update: If the interface has changed, this option should be True.

        Returns:
            The element if it was found.

        Raises:
            NoSuchElementException - If the element wasn't found.

        Usage:
            element = driver.find_element_by_id('foo')
        '''
        return self.find_element(by=By.ID, value=id_, update=update)

    def find_elements_by_id(self, id_, update=False) -> Elements:
        '''Finds multiple elements by id.

        Args:
            id_: The id of the elements to be found.
            update: If the interface has changed, this option should be True.

        Returns:
            A list with elements if any was found. An empty list if not.

        Raises:
            NoSuchElementException - If the element wasn't found.

        Usage:
            elements = driver.find_elements_by_id('foo')
        '''
        return self.find_elements(by=By.ID, value=id_, update=update)

    def find_element_by_name(self, name, update=False) -> Elements:
        '''Finds an element by name.

        Args:
            name: The name of the element to be found.
            update: If the interface has changed, this option should be True.

        Returns:
            The element if it was found.

        Raises:
            NoSuchElementException - If the element wasn't found.

        Usage:
            element = driver.find_element_by_name('foo')
        '''
        return self.find_element(by=By.NAME, value=name, update=update)

    def find_elements_by_name(self, name, update=False) -> Elements:
        '''Finds multiple elements by name.

        Args:
            name: The name of the elements to be found.
            update: If the interface has changed, this option should be True.

        Returns:
            A list with elements if any was found. An empty list if not.

        Raises:
            NoSuchElementException - If the element wasn't found.

        Usage:
            elements = driver.find_elements_by_name('foo')
        '''
        return self.find_elements(by=By.NAME, value=name, update=update)

    def find_element_by_class(self, class_, update=False) -> Elements:
        '''Finds an element by class.

        Args:
            class_: The class of the element to be found.
            update: If the interface has changed, this option should be True.

        Returns:
            The element if it was found.

        Raises:
            NoSuchElementException - If the element wasn't found.

        Usage:
            element = driver.find_element_by_class('foo')
        '''
        return self.find_element(by=By.CLASS, value=class_, update=update)

    def find_elements_by_class(self, class_, update=False) -> Elements:
        '''Finds multiple elements by class.

        Args:
            class_: The class of the elements to be found.
            update: If the interface has changed, this option should be True.

        Returns:
            A list with elements if any was found. An empty list if not.

        Raises:
            NoSuchElementException - If the element wasn't found.

        Usage:
            elements = driver.find_elements_by_class('foo')
        '''
        return self.find_elements(by=By.CLASS, value=class_, update=update)

    def __repr__(self):
        return '<{0.__module__}.{0.__name__} (device="{1}")>'.format(type(self), self.device_sn)

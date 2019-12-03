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
from .service import _PATH, Service
from .utils import merge_dict


class BaseAndroidDriver(Service):
    '''Controls Android Debug Bridge and allows you to drive the android device.'''

    _element_cls = Elements
    _temp = os.path.join(tempfile.gettempdir(), 'uidump.xml')
    _nodes = None

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

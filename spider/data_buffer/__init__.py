# Embedded file name: /work/build/source/athena/utils/data_buffer/__init__.py
from buffer import *

def create(url):
    return BufferFactory().create(url)
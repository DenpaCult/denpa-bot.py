"""
Copied from w3schools
for use in MusicPlayer.hist
"""
from typing import Generic, TypeVar

T = TypeVar("T")
class Stack(Generic[T]): # am i doing this right?

    def __init__(self, lst: list[T] = []):
        self.stack: list[T] = lst

    def push(self, element):
        self.stack.append(element)

    def pop(self):
        if self.isEmpty():
            return "Stack is empty"
        return self.stack.pop()

    def peek(self):
        if self.isEmpty():
            return "Stack is empty"
        return self.stack[-1]

    def isEmpty(self):
        return len(self.stack) == 0

    def size(self):
        return len(self.stack)

    def all(self):
        return self.stack

    def reveresed(self):
        return reversed(self.stack)

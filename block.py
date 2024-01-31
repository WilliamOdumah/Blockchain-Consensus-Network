from message import Message
import time
import hashlib
from typing import List
import json

class Block:
    def __init__(self, miner, messages, prev_hash, height, nonce, hash, timestamp=None, is_genesis=False):
        self.miner = miner
        self.messages = messages[:10]  # Only the first 10 messages are included
        self.prev_hash = prev_hash
        self.height = height
        self.nonce = nonce
        self.hash = hash
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.is_genesis = is_genesis

        print("*************************\n*                       *\n*                       *\n*   BLOCK"+ str(self.height)+" CREATED    *\n*                       *\n*                       *\n*************************")
    
    def compute_hash(self):
        """
        Compute the hash of the block's contents, considering the difficulty.
        """
        hashBase = hashlib.sha256()

        # Add the previous block's hash unless it's the genesis block
        if not self.is_genesis:
            hashBase.update(self.prev_hash.encode())

        # Add the miner's name
        hashBase.update(self.miner.encode())

        # Add the messages in order
        for message in self.messages:
             # Check if message is a Message instance or a string
            if isinstance(message, Message):
                # If it's a Message instance, use its content
                hashBase.update(message.content.encode())
            else:
                # If it's a string, use it directly
                hashBase.update(message.encode())

        # Convert timestamp to integer and then to bytes
        int_timestamp = int(self.timestamp)
        hashBase.update(int_timestamp.to_bytes(8, 'big'))

        # Add the nonce
        hashBase.update(self.nonce.encode())

        # Compute and return the hash
        return hashBase.hexdigest()
    
    def add_block(self, block):
        if block.height == len(self.chain) and block.prev_hash == self.get_last_block().hash:
            self.chain.append(block)
            return True
        return False
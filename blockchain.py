from block import Block
from typing import List

from block import Block
from typing import List

class Blockchain:
    def __init__(self, difficulty):
        self.difficulty = difficulty
        self.chain: List[Block] = []
        print("Empty chain initialized")

    def add_block(self, block: Block):
        """
        Add a new block to the blockchain if it is valid.
        """
        if self.is_valid_block(block):
            self.chain.append(block)
            return True
        return False

    def is_valid_block(self, block: Block):
        """
        Check if a block is valid: correct height, prev_hash, and hash.
        """
        # Handle the case when the blockchain is empty
        if not self.chain:
            return block.height == 0
        else:
            last_block = self.chain[-1]
            if block.height != last_block.height + 1:
                return False
            if block.prev_hash != last_block.hash:
                return False
            if not block.hash.endswith('0' * self.difficulty):
                return False
            return block.hash == block.compute_hash()

    def get_last_block(self):
        """
        Return the last block in the chain.
        """
        return self.chain[-1] if self.chain else None
    
    def expected_next_block_height(self):
        """
        Return the height of the next block expected in the blockchain.
        """
        # The next block's height is one more than the height of the last block.
        # If the chain is empty, the height of the next block (genesis block) is 0.
        return len(self.chain)



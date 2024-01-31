class ConsensusAlgorithm:
    def __init__(self, blockchain, network_handler):
        self.blockchain = blockchain
        self.network_handler = network_handler
        self.chain_stats = {}
        self.peer_stats = {}  # Dictionary to keep track of stats by peer
        self.difficulty = blockchain.difficulty
        self.current_hash = 0

            
    def handle_stats_reply(self, stats, addr):
        height = stats.get('height')
        hash_value = stats.get('hash')
        self.current_hash =hash_value
        if height is not None and hash_value is not None:
            peer_id = f"{addr[0]}:{addr[1]}"
            self.peer_stats[peer_id] = {'height': height, 'hash': hash_value}
            print(f"Stats received from peer {peer_id}: height={height}, hash={hash_value}")
    
    
    def find_longest_chain(self):
        my_chain_height = len(self.blockchain.chain)  # Start with your blockchain height
        my_chain_hash = self.blockchain.get_last_block().hash if my_chain_height > 0 else None
        highest_height = my_chain_height
        highest_hash = my_chain_hash
        peers_for_highest_chain = []

        for peer_id, stats in self.peer_stats.items():
            height = stats.get('height')
            hash_value = stats.get('hash')
            
            # Only consider non-null heights and valid hashes
            if height != 'null' and self.is_hash_valid(hash_value, self.difficulty):
                height = int(height)  # Convert height to integer

                if height > highest_height:
                    highest_height = height
                    highest_hash = hash_value
                    peers_for_highest_chain = [peer_id]
                elif height == highest_height and hash_value == highest_hash:
                    peers_for_highest_chain.append(peer_id)

        # Check if your blockchain is already up to date
        if highest_height <= my_chain_height:
            print("Blockchain is already up to date.")
        else:
            # Request blocks from peers with the highest valid chain
            print(f"About to request blocks from height {highest_height} from the highest valid chain.")
            self.network_handler.consensus_peers = peers_for_highest_chain
            self.network_handler.request_blocks_from_peers(highest_height)



    def is_hash_valid(self, hash_value, difficulty):
            # Check if the hash ends with a sufficient number of zeros
            return hash_value.endswith('0' * difficulty)
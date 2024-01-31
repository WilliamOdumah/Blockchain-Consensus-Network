class Node:
    def __init__(self, address, blockchain, consensus_algorithm, network_handler):
        self.address = address
        self.blockchain = blockchain
        self.consensus_algorithm = consensus_algorithm
        self.network_handler = network_handler
        self.network_handler.consensus_algorithm = self.consensus_algorithm  # Link consensus algorithm to network handler
        
    def join_network(self):
        # Initiate the consensus process
        self.network_handler.initiate_consensus()

    def create_message(self, sender, recipient, content):
        # Creates a new message
        pass
        
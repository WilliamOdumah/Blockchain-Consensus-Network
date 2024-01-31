from message import Message
from block import Block
import socket
import json
import uuid
import time
import random

# Network configuration constants
MAX_PEERS = 3
WELL_KNOWN_HOST = 'silicon.cs.umanitoba.ca'
WELL_KNOWN_PORT = 8999
GOSSIP_INTERVAL = 30  # seconds
PEER_TIMEOUT = 60  # seconds
RE_REQUEST_RATE = 10 # Number of peer we re-request from at a time to speed up replies
STAT_WAIT_ROUNDS = 10

class NetworkHandler:
    def __init__(self, port, blockchain):
        self.host = self.get_local_ip()  # Fetch the local IP
        self.port = port
        print("My host = "+str(self.host)+". My port = "+str(self.port))
        self.peers = {}  # Store peers as {id: (host, port)}
        self.received_gossips = set()  # Store received gossip IDs to prevent repeats
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
        self.socket.bind((self.host, self.port))
        self.socket.setblocking(False)  # Set the socket to non-blocking
        self.consensus_algorithm = None  # This will be set by the Node class
        self.is_consensus_ongoing = False  # Flag to track consensus state
        self.blockchain = blockchain  # Initialize the blockchain instance
        self.sent_gossip_ids = set()  # Blacklist of sent gossip IDs
        self.repeated_gossip_encountered = False  # New flag
        self.repeated_gossip_encountered_count=0
        self.temp_block_storage = {}  # Temporary storage for out-of-order blocks
        self.waiting_for_blocks = False  # Flag to indicate if waiting for blocks
        self.last_block_request_time = None  # Time when the last block request was made
        self.highest = 0
        self.active_peers = []  # List to keep track of peers who have responded
        self.block_count = 0
        self.total_blocks_requested = 0
        self.is_waiting_for_blocks = False
        self.consensus_peers = []
        self.no_get_block_response =0
        self.consensus_block_queue = []
    
    def get_local_ip(self):
        """Fetches the local IP address."""
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
            
    def listen_for_messages(self):
        while True:
            try:
                # Use recvfrom to get the message and the address of the sender
                message, addr = self.socket.recvfrom(1024)
                self.handle_incoming_message(message, addr)
            except BlockingIOError:
                # Sleep shortly to prevent a busy loop when there are no incoming messages
                time.sleep(0.1)
            # Check for peers timeout
            self.check_peers_timeout()

    def handle_incoming_message(self, message, addr):
        try:
            message = json.loads(message.decode('utf-8'))
            print("Peer message = "+str(message)+"\n")
            if message.get('id') in self.sent_gossip_ids:
                print("IGNORE BECAUSE ON BLACKLIST")
                # Ignore messages that are in the blacklist
                return
            # Determine the message type and call the appropriate handler.
            message_type = message.get('type')
            if message_type == "GOSSIP":
                self.handle_gossip(message, addr)
            elif message_type == "GOSSIP_REPLY":
                self.handle_gossip_reply(message, addr)
            elif message_type == "GET_BLOCK":
                self.handle_get_block(message, addr)
            elif message_type == "ANNOUNCE":
                self.handle_announce(message, addr)
            elif message_type == "STATS":
                self.handle_stats(addr)
            elif message_type == "STATS_REPLY":
                self.handle_stats_reply(message,addr)
            elif message_type == "CONSENSUS":
                self.handle_consensus(addr)
            elif message_type == "GET_BLOCK_REPLY":
                self.handle_get_block_reply(message, addr)
        except json.JSONDecodeError:
            pass  # Invalid JSON, ignore the message
        except AttributeError as ae:
            print(f"IGNORING INVALID MESSAGE" + str(ae))


    def check_peers_timeout(self):
            """
            Drop peers that haven't sent a message in the last minute.
            """
            current_time = time.time()
            # print("current time is = "+str(current_time))
            for peer_id, peer_info in list(self.peers.items()):
                last_seen = peer_info[2] #check last seen
                if current_time - last_seen > 60:  # 60 seconds timeout
                    print(f"Dropping peer {peer_id} due to timeout.")
                    del self.peers[peer_id]


    def handle_gossip(self, message, addr):
        # Handle an incoming GOSSIP message
        gossip_id = message.get('id')

        # Always reply to the gossip, regardless of whether it's a new or known id
        gossip_reply = {
            "type": "GOSSIP_REPLY",
            "host": self.host,
            "port": self.port,
            "name": "William"
        }
        self.send_message(gossip_reply, (message['host'], message['port']))

        # Process the gossip only if it's a new id
        if gossip_id and gossip_id not in self.received_gossips:
            self.received_gossips.add(gossip_id)
            
            # Update or add the peer's information
            self.peers[gossip_id] = (message['host'], message['port'], time.time())

            # Forward the gossip message to other peers
            self.forward_gossip(message)
        else:
            self.repeated_gossip_encountered_count= self.repeated_gossip_encountered_count+1
            if self.repeated_gossip_encountered_count == STAT_WAIT_ROUNDS:
                self.repeated_gossip_encountered = True # Request stats for after every 10 repeated gossips
                self.repeated_gossip_encountered_count = 0  # Set back to 0
        
        
    def handle_gossip_reply(self, message, addr):
        """
        Handle an incoming GOSSIP-REPLY message by storing the peer's information.
        """
        peer_host = message['host']
        peer_port = message['port']
        
        # Create a unique identifier for the peer (host:port)
        peer_id = f"{peer_host}:{peer_port}"

        # Check if this peer is already known
        if peer_id not in self.peers:
            # Store the peer's information
            self.peers[peer_id] = (peer_host, peer_port, time.time())
        else:
            print(f"GOSSIP-REPLY sender already known: {peer_host}:{peer_port}")
        
        
    def forward_gossip(self, message):
        """Forward the GOSSIP message to a random subset of known peers."""
        # Get a list of all peers
        all_peers = list(self.peers.items())

        # Randomly select a subset of peers
        selected_peers = random.sample(all_peers, min(MAX_PEERS, len(all_peers)))

        # Loop through the selected peers and send the message
        for _, peer_info in selected_peers:
            peer_host, peer_port, _ = peer_info

            try:
                self.send_message(message, (peer_host, peer_port))
            except Exception as e:
                print(f"Error forwarding gossip to {peer_host}:{peer_port}: {e}")
                
                
    def send_gossip(self):
        """Send a gossip message to announce presence."""
        print("creating gossip messsage")
        gossip_id = str(uuid.uuid4())  # Unique identifier for the gossip message
        gossip_message = {
            "type": "GOSSIP",
            "host": self.host,
            "port": self.port,
            "id": gossip_id,
            "name": "William" 
        }
        self.sent_gossip_ids.add(gossip_id)  # Add my ID to the blacklist (so i dont recieve messages from myself)
        self.send_message(gossip_message, (WELL_KNOWN_HOST, WELL_KNOWN_PORT))


    def handle_stats(self, addr):
            # Prepare the stats reply
            if self.is_consensus_ongoing:
                stats_reply = {"type": "STATS_REPLY", "message": "CURRENTLY RUNNING CONSENSUS"} 
            else:
                stats_reply = {
                    "type": "STATS_REPLY",
                    "height": len(self.blockchain.chain),  # Height of the blockchain
                    "hash": self.blockchain.get_last_block().hash if len(self.blockchain.chain) > 0 else None  # Hash of the last block
                }
            print("replying stats with = "+str(stats_reply))
            # Send the reply to the address that requested the stats
            self.send_message(stats_reply, addr)


    def handle_stats_reply(self, message, addr):
        # Forward the stats reply to the ConsensusAlgorithm for processing
        if self.consensus_algorithm:
            self.consensus_algorithm.handle_stats_reply(message, addr)


    def handle_get_block(self, message, addr):
        requested_height = message.get('height')
        if requested_height is None or requested_height >= len(self.blockchain.chain):
            print("DONT HAVE ENOUGH BLOCKS TO FULFILL THIS REQUEST")
            response = {'type': 'GET_BLOCK_REPLY', 'height': None}
        else:
            block = self.blockchain.chain[requested_height] # Blockchain index corresponds to height
            response = {
                'type': 'GET_BLOCK_REPLY',
                'hash': block.hash,
                'height': block.height,
                'messages': [msg.content for msg in block.messages],
                'minedBy': block.miner,
                'nonce': block.nonce,
                'timestamp': block.timestamp
            }
        self.send_message(response, addr)
    
    
    def handle_get_block_reply(self, message, addr):
        if any(field is None for field in [message.get('height'), message.get('minedBy'), message.get('nonce'), message.get('messages'), message.get('hash')]):
            print("Ignoring GET_BLOCK_REPLY with None fields.")
            return  # Exit the function without processing the message
        
        self.add_to_active_peers(addr)
        # Extract block data from the message
        block_height = message.get('height')
        mined_by = message.get('minedBy')
        nonce = message.get('nonce')
        messages = message.get('messages')
        block_hash = message.get('hash')
        timestamp = message.get('timestamp')
        
        try:
            self.blockchain.chain[block_height] # If I am able to select the chain. It means it already exists
            print("This block already exists in the chain")
        except IndexError:
             # Determine the previous hash
            last_block = self.blockchain.get_last_block()
            prev_hash = '0' if last_block is None else last_block.hash

            # Create a block object
            new_block = Block(miner=mined_by, messages=messages, prev_hash=prev_hash, height=block_height, timestamp=timestamp, nonce=nonce, hash=block_hash)
            self.block_count = self.block_count + 1 
      
            if block_height == self.blockchain.expected_next_block_height():
                # Add block to blockchain if it's the next expected block
                # Verify and add the block to the blockchain
                if self.blockchain.is_valid_block(new_block):
                    self.blockchain.add_block(new_block)
                    print("Block "+str(block_height)+" added to the blockchain.")
                else:
                    print("Invalid block received.")
            else:
                # Store block in temporary storage if it's out of order
                self.temp_block_storage[block_height] = new_block
                print("Block "+str(block_height)+" queued to enforce proper blokchain order")

            # Check if there are any blocks in temporary storage that can now be added
            self.add_blocks_from_temp_storage()
        except TypeError:
            print("IGNORE invalid message")
            
          
    def add_blocks_from_temp_storage(self):
        # Add blocks from temporary storage to the blockchain in order
        print("Expected next block = "+str(self.blockchain.expected_next_block_height()))
        print(str(self.blockchain.expected_next_block_height() in self.temp_block_storage))
        while self.blockchain.expected_next_block_height() in self.temp_block_storage:
            block = self.temp_block_storage.pop(self.blockchain.expected_next_block_height())
            print("*Adding Block "+str(block.height)+" to chain from queue*")
            self.blockchain.add_block(block)
                    
                    
    def add_to_active_peers(self, addr):
            """Add a peer to the list of active peers if not already present."""
            peer_id = f"{addr[0]}:{addr[1]}"
            if peer_id not in self.active_peers:
                self.active_peers.append(peer_id)
                print(f"Added peer {peer_id} to active peers.")
                
                
    def process_consensus_queue(self):
        print("Processing consensus block queue...")
        while self.consensus_block_queue:
            # Get and remove the first block in the queue
            block = self.consensus_block_queue.pop(0)

            # Validate and add the block to the blockchain
            if self.blockchain.is_valid_block(block):
                self.blockchain.add_block(block)
                print(f"Block from queue added to blockchain: {block.hash}")
            else:
                print(f"Invalid block in queue skipped: {block.hash}")
          
            
    def handle_announce(self, message, addr):
        # Extract data from the message
        block_height = message['height']
        mined_by = message['minedBy']
        nonce = message['nonce']
        messages = message['messages']
        block_hash = message['hash']
        
        # Determine the previous hash
        last_block = self.blockchain.get_last_block()
        prev_hash = '0' if last_block is None else last_block.hash

        # Create a new Block instance from the extracted data
        new_block = Block(miner=mined_by,messages=messages,prev_hash=prev_hash,height=block_height,nonce=nonce,hash=block_hash)

        # Check if the node is currently in consensus
        if self.is_consensus_ongoing:
            # If in consensus, queue the block to be processed later
            self.consensus_block_queue.append(new_block)
            print("New block queued for processing after consensus.")
        else:
            # If not in consensus, process the block immediately
            if self.blockchain.is_valid_block(new_block):
                self.blockchain.add_block(new_block)
                print(f"New block added: {new_block.hash}")
            else:
                print("Invalid block received.")         
    
            
    def handle_consensus(self, addr):
        # Check if a consensus process is already ongoing
        if not self.is_consensus_ongoing:
            self.is_consensus_ongoing = True
            # Initiate the consensus process
            self.initiate_consensus(self.consensus_algorithm)
        else:
            # If consensus is already ongoing, ignore or handle appropriately
            print("Consensus process is already ongoing.")
        
        
    def initiate_consensus(self, consensus_algorithm):
        self.is_consensus_ongoing = True
        if consensus_algorithm is None:
            print("Not enough data to run consensus")
            
        else:
            self.consensus_algorithm = consensus_algorithm
            print("SENDING STATS MESSAGE")
            stats_request = {"type": "STATS"}
            for peer_id, (peer_host, peer_port, _) in self.peers.items():
                self.send_message(stats_request, (peer_host, peer_port))
                print("Sent STATS to a peer")
                
                
    def request_blocks_from_peers(self, highest_height):
        self.highest = highest_height
        self.total_blocks_requested = highest_height + 1
        self.start_request_time = time.time()  # Start the timer
        print("REQUESTING BLOCKS FROM PEERS")

        while not self.all_blocks_received():
            self.send_get_block_requests(highest_height)
            self.listen_for_replies(duration=5)  # Listen for 5 seconds
        self.add_blocks_from_temp_storage()
        self.process_consensus_queue()
        print("*CONSENSUS DONE. WE NOW HAVE CHAIN OF HEIGHT = "+str(len(self.blockchain.chain))+"*")
    
    
    def send_get_block_requests(self, highest_height):
        num_peers = len(self.consensus_peers)
        if num_peers == 0:
            print("No peers to request blocks from.")
            return

        # Create a set of all block heights that need to be requested
        needed_blocks = set(range(highest_height + 1)) - set(block.height for block in self.blockchain.chain) - set(self.temp_block_storage.keys())

        # If all needed blocks are already present, return
        if not needed_blocks:
            print("All needed blocks are already present.")
            return

        blocks_per_peer = len(needed_blocks) // num_peers
        extra_blocks = len(needed_blocks) % num_peers

        needed_blocks = list(needed_blocks)
        needed_blocks.sort()  # Sort the needed blocks for consistent distribution

        # Distribute the block requests among the peers
        for i, peer_id in enumerate(self.consensus_peers):
            start_index = i * blocks_per_peer
            end_index = start_index + blocks_per_peer - 1

            # Distribute extra blocks among the first few peers
            if i < extra_blocks:
                end_index += 1

            # Get the specific block heights for this peer
            block_heights_for_peer = needed_blocks[start_index:end_index + 1]

            # Send request for each block height
            for height in block_heights_for_peer:
                block_request = {"type": "GET_BLOCK", "height": height}
                peer_host, peer_port = peer_id.split(":")
                self.send_message(block_request, (peer_host, int(peer_port)))
                
                    
    def listen_for_replies(self, duration):
        print("Waiting for GET_BLOCK replies...")
        start_time = time.time()
        while time.time() - start_time < duration:
            try:
                message, addr = self.socket.recvfrom(1024)
                self.handle_incoming_message(message, addr)
            except BlockingIOError:
                continue  # No message received, continue listening
            self.check_peers_timeout()
            
            
    def all_blocks_received(self):
        print("checking if all blocks recieved...")
        return (self.block_count >= self.total_blocks_requested)  


    def force_consensus(self, peer_host, peer_port):
        consensus_message = {"type": "CONSENSUS"}
        try:
            self.send_message(consensus_message, (peer_host, peer_port))
            print(f"Sent CONSENSUS request to {peer_host}:{peer_port}")
        except Exception as e:
            print(f"Failed to send CONSENSUS request: {str(e)}")
        

    def send_message(self, message, addr):
            # Send a UDP message to the specified address
            print("My message = "+str(message)+"\n")
            try:
                message_json = json.dumps(message).encode('utf-8')
                self.socket.sendto(message_json, addr)
            except Exception as e:
                print(f"Socket error: {str(e)}")


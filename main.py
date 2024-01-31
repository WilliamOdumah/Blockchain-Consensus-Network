from blockchain import Blockchain
from consensus import ConsensusAlgorithm
from network_handler import NetworkHandler
import time
DIFFICULTY = 8
GOSSIP_INTERVAL = 30
STATS_TIMEOUT = 30
STATS_REQUEST_ROUND = 4   # Send STATS requests on this round of gossips

def main():
    try:
        # Initialize the blockchain and other components
        print("Starting....")
        blockchain = Blockchain(difficulty=DIFFICULTY)
        print("Blockchain set")

        # Initialize the network handler
        network_handler = NetworkHandler(port=9023, blockchain=blockchain)
        print("Network set")

        # Initialize the consensus algorithm
        consensus_algorithm = ConsensusAlgorithm(blockchain, network_handler)
        print("Consensus set")

        # Send initial gossip message to join the network
        network_handler.send_gossip()
        print("Initial gossip message sent")
        
        
        # # # Initiate consensus process after joining the network
        # network_handler.initiate_consensus()
        # consensus_algorithm.find_longest_chain()
        
        # Initialize a counter for gossip messages
        gossip_counter = 0

        # Last time a gossip message was sent
        last_gossip_time = time.time()
        print("last gossip time = "+str(last_gossip_time))
        
        has_paused_for_stats = False  # Flag to ensure pause happens only once
        has_requested_stats = False 


        print("Waiting for incoming messages...")
        # Main loop
        while True:
            if not has_paused_for_stats and network_handler.repeated_gossip_encountered:
                # Pause the loop to handle stats and consensus
                print("***Repeated gossip encountered. Initiating stats request and consensus.***")
                # Initiate consensus for the first time after a number of repeated gossips encountered
                network_handler.initiate_consensus(consensus_algorithm=consensus_algorithm)
                print("***Stats requested and consensus initiated. Resuming normal operations.***")

                # Mark that we have paused and handled stats and consensus
                has_paused_for_stats = True
                has_requested_stats = True
                last_stats_request_time = current_time
                # Reset the flag to continue the loop
                network_handler.repeated_gossip_encountered = False
            else:
                pass
            
            # Check for incoming messages
            try:
                message, addr = network_handler.socket.recvfrom(1024)
                network_handler.handle_incoming_message(message, addr)
            except BlockingIOError:
                # No message received, normal for non-blocking sockets
                pass
            
            # Check if any peers have timed out
            network_handler.check_peers_timeout()

            # Send gossip message at regular intervals
            current_time = time.time()
            if current_time - last_gossip_time >= GOSSIP_INTERVAL:
                network_handler.send_gossip()
                print("Waiting for incoming messages...")
                last_gossip_time = current_time
                gossip_counter += 1
                
                if network_handler.is_waiting_for_blocks:
                    # Pause operations and wait for blocks
                    if network_handler.all_blocks_received() :
                        network_handler.is_waiting_for_blocks = False
                        network_handler.is_consensus_ongoing = False
                        
                        # Resume normal operations
                        # Request stats every 4th gossip (every 120 seconds)
                        if gossip_counter % STATS_REQUEST_ROUND == 0 and has_paused_for_stats:
                            network_handler.initiate_consensus(consensus_algorithm)
                            has_requested_stats = True
                            last_stats_request_time = current_time
                    else:
                        pass
                else:
                    # Resume normal operations
                    # Request stats every 4th gossip (every 120 seconds)
                    if gossip_counter % STATS_REQUEST_ROUND == 0 and has_paused_for_stats:
                        network_handler.initiate_consensus(consensus_algorithm)
                        has_requested_stats = True
                        last_stats_request_time = current_time
                        # consensus_algorithm.find_longest_chain()

            else:
                pass
                    
            # Find longest chain 30 seconds after requesting stats (gives peers time to reply)
            if has_requested_stats and last_stats_request_time and current_time - last_stats_request_time >= STATS_TIMEOUT:
                print("Now finding longest chain and getting blocks...")
                consensus_algorithm.find_longest_chain()
                last_stats_request_time = 0  # Reset the timer
                has_requested_stats = False
                network_handler.is_waiting_for_blocks = True

            # Sleep to avoid busy waiting
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Program interrupted by the user, exiting.")

if __name__ == "__main__":
    main()

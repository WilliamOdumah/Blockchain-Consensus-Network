Starting the Peer:
    To start the peer: Run main.py with Python 3.
    Command Line Arguments: None required. The application starts on a predefined port (e.g., 9023).
    Synchronization Time: Synchronization time varies depending on network conditions and the number of peers but typically completes within a few minutes.
    Expected Output: The application logs messages indicating its progress on connecting to peers, receiving gossip, and synchronizing the blockchain. Once my peer has sent a gossip the console will print the gossip replies recieved from other peers on the network, along with other messages such as GOSSIP, STATS, ANNOUNCE and CONSENSUS


Key Functionalities:
Gossip Protocol
    Implementation: network_handler.py
    Description: Sends GOSSIP messages every 30 seconds (because assignment instructions say time out occurs after a minute). Replies to received GOSSIP messages with GOSSIP-REPLY.
    Relevant Code: Look for send_gossip(), handle_gossip() and handle_gossip_reply() methods in network_handler.py.

Block Collection and Load Balancing
    Implementation: network_handler.py
    Description: Requests for blocks are distributed among known peers to evenly load balance the data retrieval.
    Relevant Code: See request_blocks_from_peers() and send_get_block_requests() in network_handler.py.

Chain Verification
    Implementation: blockchain.py
    Description: Each block in the chain is verified for its integrity and position.
    Relevant Code: The is_valid_block() and comput_hash() method in blockchain.py performs the verification.

Handling New Blocks (ANNOUNCE)
    Implementation: network_handler.py
    Description: New blocks received via ANNOUNCE messages are added to the top of the chain if valid.
    Relevant Code: Check handle_announce() in network_handler.py.

Stats Collection
    Implementation: network_handler.py
    Description: Sends STATS messages to all known peers and collects results to aid in the consensus process.
    Relevant Code: The initiate_consensus() and handle_stats_reply() methods in network_handler.py.

Consensus Mechanism:
    File: consensus.py
    Method: find_longest_chain()
    Location: Line 21.
    Description: This method determines the longest valid blockchain among all peers. It compares the heights and hashes of chains received from peers, selecting the highest one that meets the network's difficulty criteria, ensuring the chain's validity.
    If the "CONSENSUS" messgae is used before a natural consensus occurs, my terminal will print "not enough data to run consensus"

Peer Cleanup Process:
    File: network_handler.py
    Method: check_peers_timeout()
    Location: Line 94.
    Description: This method cleans up peers that haven't communicated within a specified timeout period (60 seconds). It iterates through the list of known peers and removes any that have not sent a message recently, ensuring the list remains up-to-date and active.


Summary:(Program Workflow and State Transitions)
    My code uses a combination of timers and triggers to change state.
    At the program's start, all necessary classes (Blockchain, ConsensusAlgorithm, NetworkHandler, etc.) are initialized.
    A last_gossip_time tracker is set up to manage the interval for sending gossip messages based on the GOSSIP_INTERVAL constant.
    
    The program sends gossip messages every 30 seconds as a keep-alive signal.
    Peer activity is monitored, and any peer that has not sent a gossip message within the last minute is removed from the peer list.

    Initially, stats requests are triggered only after a certain number of repeated gossips have been observed. This delay allows time for accumulating a sufficient number of peers before initiating consensus.
    After the initial pause and stats request, subsequent stats requests are made at regular intervals (every 2 minutes) to ensure the network's current state is known.
    The program listens for incoming messages continuously. However, during consensus, stats requests are not made nor responded to, focusing on building the blockchain.

    Acquiring all necessary blocks for the blockchain proved to be time-consuming, especially if there are many blocks to process.
    Blocks are added to the blockchain only if they are valid and in the correct order. Temporary storage is used for out-of-order blocks, which are added once the missing blocks are received. An ANNOUNCEd block is put in a queue till i have its preceeding block
    The process involves several checks and flags to ensure the blocks are added correctly and the blockchain's integrity is maintained.

    Resilience and Challenges:
    The code is designed to be resilient to various network issues and invalid messages, which are ignored.
    One of the main challenges faced was acquiring all the blocks needed for the blockchain, particularly when dealing with a large number of blocks. I however ensure my chain is in ourder and valid even if it is outdated

    Key Flags and Conditions:
    The program uses a variety of flags to control the flow of operations. These flags determine when to request stats, respond to messages, initiate consensus, and handle blocks.
    The use of these flags ensures that each process occurs at the appropriate time and that the program's different components work together harmoniously.

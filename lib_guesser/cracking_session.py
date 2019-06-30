#!/usr/bin/env python3

################################################################################
#
# Name: PCFG_Cracker Cracking Management Code
# Description: Manages a cracking session
#
#              Making this a class to help support different guess generation
#              modes in the future
#
################################################################################


import sys
import traceback
import time
import threading # Used only for the "check for user input" threads

# Local imports
from .priority_queue import PcfgQueue
from .status_report import StatusReport


## Used to manage a password cracking session
#
class CrackingSession:
    
    
    ## Basic initialization function
    #
    def __init__(self, pcfg, save_config, save_filename):
    
        # Used to save a session's status to disk
        self.save_config = save_config
        self.save_filename = save_filename
       
        # Initalize the status report class for providing debugging and
        # status information
        self.report = StatusReport()
    
        # Save the grammar for easy reference
        self.pcfg = pcfg
        
        # The guessing session modes
        self.mode = "priority_queue"          
        
        
    ## Starts the cracking session and starts generating guesses
    #
    def run(self, load_session = False):
        
        ## New session
        #
        if not load_session:
        
            # Initalize the priority queue
            self.pqueue = PcfgQueue(self.pcfg)
            
            # Save the inital restore file 
            self._save_session()
        
        ## Load session described in previously saved configfile
        #        
        else:
            print ("Restoring saved progress...",file=sys.stderr)
            # Update the status report so things like probability coverage
            # reflect what was done before
            self.report.load(self.save_config)
            
            # Update the priority queue to skip over pre-terminals that have
            # been guessed previously
            self.pqueue = PcfgQueue(self.pcfg, self.save_config)
        
        print ("Starting to generate password guesses",file=sys.stderr)
        print ("Press [ENTER] to display a status output",file=sys.stderr)
        print ("Press 'q' [ENTER] to exit",file=sys.stderr)
        
        ## Set up the check to see if a user is pressing a button
        #
        user_thread = threading.Thread(target=keypress, args=(self.report, self.pcfg))
        user_thread.daemon = True  # thread dies when main thread (only non-daemon thread) exits.
        user_thread.start()
                            
        # Keep running while the p_queue.next_function still has items in it
        while True:
                 
            ## Get the next item from the pqueue
            #
            pt_item = self.pqueue.next()
            
            # If the pqueue is empty, there are no more guesses to make
            if pt_item == None:
                print ("Done processing the PCFG. No more guesses to generate",file=sys.stderr)
                print ("Shutting down guessing session",file=sys.stderr)
                return
                    
            # Check to see if the program should exit based on user input
            #
            # DevNote: Doing this after we get an item from the pqueue so if
            #          the session shuts down we save the probability of
            #          this item and don't repeat the previous pt that was
            #          popped off and already guessed.
            #
            #          Note: In some rare cases the probability of this pt and
            #          the prev one might be the same in which case both will
            #          be repeated if this session restarts. That's not ideal
            #          but shouldn't have a noticable impact when people restarts
            #          sessions.
            #
            if not user_thread.is_alive():
                print("Saving Session Info",file=sys.stderr)
                self._save_session()
                print("Exiting...",file=sys.stderr)
                break    
            
            # Update stats after the save might occur so we don't double count
            # them when restoring a session
            self.report.num_parse_trees += 1
            self.report.pt_item = pt_item
          
            try:
                num_generated_guesses = self.pcfg.create_guesses(pt_item['pt'])
                self.report.num_guesses += num_generated_guesses
                
                self.report.probability_coverage += pt_item['prob'] * num_generated_guesses
            
            # The receiving program is no longer accepting guesses
            # Usually occurs after all passwords have been cracked
            except OSError:
                break
                            
        return
        
        
    ## Saves a gussing session's status to disk
    #    
    def _save_session(self):
     
        # Update the status report information
        self.report.update_save_config(self.save_config)
    
        # Update the guessing session information
        self.save_config.set('guessing_info', 'mode', self.mode)
        
        # Priority Queue Mode
        if self.mode == "priority_queue":
            self.pqueue.update_save_config(self.save_config)
    
        # Save the configuration file
        try:
            with open(self.save_filename, 'w') as configfile:
                self.save_config.write(configfile)
                
        except IOError as error:
            print (error)
            print ("Error writing sessiong restore file: " + self.save_filename)
            return False
        
        return True    

## Used to check to see if a key was pressed to output program status
#
# *Hopefully* should work on multiple OSs
# --Simply check user_input_char to see if it is not none
#
def keypress(report, pcfg):
    while True:
        user_input = input()
        
        # Display the status report
        report.print_status(pcfg)
        
        # If the program should exit
        if user_input == 'q':
            print( "",file=sys.stderr)
            print ("Exit command received",file=sys.stderr)
            print ("Will exit after finishing processing current pre-terminal",file=sys.stderr)
            print ("Note: If this takes too long, you can also use CTRL-C",file=sys.stderr)
            print ("      but if you exit early and later restart the session ",file=sys.stderr)
            print ("      it will begin with the previous pre-terminal",file=sys.stderr)
            print ("",file=sys.stderr)
            return
            
        # Print the help screen
        elif user_input == 'h':
            print( "",file=sys.stderr)
            report.print_help()
        
        print( "",file=sys.stderr)
        print("Press [ENTER] to display an updated status output",file=sys.stderr)
        print("Press 'h' [ENTER] for help on what the status reports mean",file=sys.stderr)
        print("Press 'q' [ENTER] to exit",file=sys.stderr)
        print( "",file=sys.stderr)
        
        


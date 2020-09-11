# Skeram World Buffs Discord Bot

Creates and updates the world buffs message and posts to the world-buff-time channel on the WoW Skeram server Discord via commands


!swb-help 


!swb-rend <time>
!swb-ony <time>
!swb-nef <time>
  ####Specifies the <time> when the buff is open/off CD


!swb-bvsf <time>
!swb-bvsf-clear 
  ####Sets the next <time> the BVSF flower should be up or clears it


!swb-rend-drop <name> <time>
!swb-ony-drop <name> <time>
!swb-nef-drop <name> <time>
!swb-hakkar-drop <name> <time>
  ####Adds the <name> of a buff dropper and the planned <time>


!swb-rend-drop-remove <name>
!swb-ony-drop-remove <name>
!swb-nef-drop-remove <name>
!swb-hakkar-drop-remove <name>
  ####Removes the <name> of a buff dropper


!swb-yi-sums-add <name> [note...]
!swb-bb-sums-add <name> [note...]
!swb-bvsf-sums-add <name> [note...]
!swb-dmt-sums-add <name> [note...]
!swb-dmf-sums-add <name> [note...]
!swb-aq-sums-add <name> [note...]
!swb-brm-sums-add <name> [note...]
  ####Adds the <name> of a summoner and the [note] which may contain cost or other info


!swb-yi-sums-remove <name>
!swb-bb-sums-remove <name>
!swb-bvsf-sums-remove <name>
!swb-dmt-sums-remove <name>
!swb-dmf-sums-remove <name>
!swb-aq-sums-remove <name>
!swb-brm-sums-remove <name>
  ####Removes the <name> of a summoner


!swb-dmt-buffs-add <name> [note...]
!swb-dmt-buffs-remove <name>
  ####Adds the <name> of a DMT buff seller and the [note] which may contain cost or other info or Removes the <name> of the DMT buffer


!swb-dmf-loc [location...]
  ####Specifies the [location] of the DMF (Elwynn Forest or Mulgore) - specifying no location will hide the message when no summoners are present


!swb-server-status [message...]
  ####Specifies the maintenance or server status [message] - specifying no message will hide the message


!swb-ally [message...]
  ####Specifies the ally sighting / griefing [message] - specifying no message will hide the message


!swb-extra-msg [message...]
  ####Specifies an additional footer [message] - specifying no message will hide the message


![Sample Bot Updated Message](https://github.com/govagent26/skeram-world-buffs/blob/master/sample_message.JPG)

# bot.py
import os
import random
import re

from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pytz import timezone

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('WORLD_BUFF_CHANNEL_ID'))

bot = commands.Bot(command_prefix='!swb-')
bot.remove_command('help')


class Dropper:
    def __init__(self, t=0, n=0):
        self.time = t
        self.name = n

class SummonerBuffer:
    def __init__(self, n=0, m=0):
        self.name = n
        self.msg = m


playback_updates = True
server_maintenance = ''
rend_time = "?:??"
rend_drops = []
ony_time = "?:??"
ony_drops = []
nef_time = "?:??"
nef_drops = []
hakkar_drops = []
hakkar_yi_summons = []
hakkar_bb_summons = []
bvsf_time = "?:??"
bvsf_summons = []
dmt_buffs = []
dmt_summons = []
aq_summons = []
brm_summons = []
dmf_location = ''
dmf_summons = []
alliance = ''
extra_message = ''



@bot.command(name="help", description="Shows all available commands")
async def help(ctx):
    helptext = "```"
    helptext += '{0.command_prefix}{1.qualified_name} {1.signature}\n\n'.format(bot, bot.get_command('help'))
    for cog in bot.cogs:
        commands = ''
        cog_obj = bot.get_cog(cog)
        for command in cog_obj.get_commands():
            commands += '\n{0.command_prefix}{1.qualified_name} {1.signature}'.format(bot, command)
        helptext += '{0}\n  {1.qualified_name}\n\n'.format(commands, cog_obj)
    helptext += "```"
    await ctx.send(helptext)

@bot.command(name="playback", description="Updates if bot should print out when changes occur [on|off]")
async def help(ctx, status):
    if status.lower() == 'on':
        playback_updates = True
    else:
        playback_updates = False
    await ctx.send('Playback is ' + ('enabled' if status == 'on' else 'disabled'))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound) or isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send('**Unknown command entered or parameters are missing** - a list of commands and usage can be found using !swb-help')
        return
    raise error


class BuffAvailTimeCommands(commands.Cog, name='Specifies the <time> when the buff is open/off CD'):
    @commands.command(name='rend', brief='Set time for when rend is open/off CD', help='Sets the next available time rend buff is open - example: !rend 2:54pm')
    @commands.has_role('World Buff Coordinator')
    async def set_rend_time(self, ctx, time):
        global rend_time
        rend_time = time
        await post_in_world_buffs_chat_channel()
        await playback_message(ctx, 'Rend buff timer updated to:\n' + await calc_rend_msg())

    @commands.command(name='ony', brief='Set time for when ony is open/off CD', help='Sets the next available time ony buff is open - example: !ony 2:54pm')
    @commands.has_role('World Buff Coordinator')
    async def set_ony_time(self, ctx, time):
        global ony_time
        ony_time = time
        await post_in_world_buffs_chat_channel()
        await playback_message(ctx, 'Ony buff timer updated to:\n' + await calc_ony_msg())

    @commands.command(name='nef', brief='Set time for when nef is open/off CD', help='Sets the next available time nef buff is open - example: !nef 2:54pm')
    @commands.has_role('World Buff Coordinator')
    async def set_nef_time(self, ctx, time):
        global nef_time
        nef_time = time
        await post_in_world_buffs_chat_channel()
        await playback_message(ctx, 'Nef buff timer updated to:\n' + await calc_nef_msg())


class BVSFBuffCommands(commands.Cog, name = 'Sets the next <time> the BVSF flower should be up or clears it'):
    @commands.command(name='bvsf', brief='Set time when BVSF is up', help='Sets the next time bvsf flower buff is up - example: !bvsf 2:54pm')
    @commands.has_role('World Buff Coordinator')
    async def set_bvsf_time(self, ctx, time):
        global bvsf_time
        if await validate_time_format(time):
            bvsf_time = time
            await post_in_world_buffs_chat_channel()
            await playback_message(ctx, 'BVSF buff timer updated to:\n' + await calc_bvsf_msg())
        else:
            await ctx.send('Invalid time provided, format must be (H)H:MM[am|pm] - example: !bvsf 2:54pm')

    @commands.command(name='bvsf-clear', brief='Clears BVSF time, sets to ?:??', help='Sets the BVSF time to ?:?? - example: !bvsf-clear')
    @commands.has_role('World Buff Coordinator')
    async def clear_bvsf_time(self, ctx):
        global bvsf_time
        bvsf_time = '?:??'
        await post_in_world_buffs_chat_channel()
        await playback_message(ctx, 'BVSF buff timer updated to:\n' + await calc_bvsf_msg())


class BuffDropAddCommands(commands.Cog, name='Adds the <name> of a buff dropper and the planned <time>'):
    @commands.command(name='rend-drop', brief='Add user that will drop rend along with drop time', help='Sets a rend confirmed dropper - example: !rend-drop Thatguy 2:54pm')
    @commands.has_role('World Buff Coordinator')
    async def set_rend_dropper(self, ctx, name, time):
        global rend_drops
        if await validate_time_format(time):
            await add_dropper(rend_drops, name, time)
            await post_in_world_buffs_chat_channel()
            await playback_message(ctx, 'Rend buff timer updated to:\n' + await calc_rend_msg())
        else:
            await ctx.send('Invalid time provided, format must be (H)H:MM[am|pm] - example: !rend-drop Thatguy 2:54pm')

    @commands.command(name='ony-drop', brief='Add user that will drop ony along with drop time', help='Sets a ony confirmed dropper - example: !ony-drop Thatguy 2:54pm')
    @commands.has_role('World Buff Coordinator')
    async def set_ony_dropper(self, ctx, name, time):
        global ony_drops
        if await validate_time_format(time):
            await add_dropper(ony_drops, name, time)
            await post_in_world_buffs_chat_channel()
            await playback_message(ctx, 'Ony buff timer updated to:\n' + await calc_ony_msg())
        else:
            await ctx.send('Invalid time provided, format must be (H)H:MM[am|pm] - example: !ony-drop Thatguy 2:54pm')

    @commands.command(name='nef-drop', brief='Add user that will drop nef along with drop time', help='Sets a nef confirmed dropper - example: !nef-drop Thatguy 2:54pm')
    @commands.has_role('World Buff Coordinator')
    async def set_nef_dropper(self, ctx, name, time):
        global nef_drops
        if await validate_time_format(time):
            await add_dropper(nef_drops, name, time)
            await post_in_world_buffs_chat_channel()
            await playback_message(ctx, 'Nef buff timer updated to:\n' + await calc_nef_msg())
        else:
            await ctx.send('Invalid time provided, format must be (H)H:MM[am|pm] - example: !nef-drop Thatguy 2:54pm')

    @commands.command(name='hakkar-drop', brief='Add user that will drop hakkar along with drop time', help='Sets a hakkar confirmed dropper - example: !hakkar-drop Thatguy 2:54pm')
    @commands.has_role('World Buff Coordinator')
    async def set_hakkar_dropper(self, ctx, name, time):
        global hakkar_drops
        if await validate_time_format(time):
            await add_dropper(hakkar_drops, name, time)
            await post_in_world_buffs_chat_channel()
            await playback_message(ctx, 'Hakkar buff timer updated to:\n' + await calc_hakkar_msg())
        else:
            await ctx.send('Invalid time provided, format must be (H)H:MM[am|pm] - example: !hakkar-drop Thatguy 2:54pm')


class BuffDropRemoveCommands(commands.Cog, name='Removes the <name> of a buff dropper'):
    @commands.command(name='rend-drop-remove', brief='Remove user dropping rend', help='Removes a rend confirmed dropper - example: !rend-drop-remove Thatguy')
    @commands.has_role('World Buff Coordinator')
    async def remove_rend_dropper(self, ctx, name):
        global rend_drops
        if await remove_summoner_buffer_dropper(rend_drops, name):
            await playback_message(ctx, 'Rend buff timer updated to:\n' + await calc_rend_msg())

    @commands.command(name='ony-drop-remove', brief='Remove user dropping ony', help='Removes a ony confirmed dropper - example: !ony-drop-remove Thatguy')
    @commands.has_role('World Buff Coordinator')
    async def remove_ony_dropper(self, ctx, name):
        global ony_drops
        if await remove_summoner_buffer_dropper(ony_drops, name):
            await playback_message(ctx, 'Ony buff timer updated to:\n' + await calc_ony_msg())

    @commands.command(name='nef-drop-remove', brief='Remove user dropping nef', help='Removes a nef confirmed dropper - example: !nef-drop-remove Thatguy')
    @commands.has_role('World Buff Coordinator')
    async def remove_nef_dropper(self, ctx, name):
        global nef_drops
        if await remove_summoner_buffer_dropper(nef_drops, name):
            await playback_message(ctx, 'Nef buff timer updated to:\n' + await calc_nef_msg())

    @commands.command(name='hakkar-drop-remove', brief='Remove user dropping hakkar', help='Removes a hakkar confirmed dropper - example: !hakkar-drop-remove Thatguy')
    @commands.has_role('World Buff Coordinator')
    async def remove_hakkar_dropper(self, ctx, name):
        global hakkar_drops
        if await remove_summoner_buffer_dropper(hakkar_drops, name):
            await playback_message(ctx, 'Hakkar buff timer updated to:\n' + await calc_hakkar_msg())


class SummonerAddCommands(commands.Cog, name='Adds the <name> of a summoner and the [note] which may contain cost or other info'):
    @commands.command(name='yi-sums-add', brief='Add user that is summoning to YI', help='Adds a YI summoner with cost/message - example: !yi-sums-add Thatguy 5g w/port')
    @commands.has_role('World Buff Coordinator')
    async def add_hakkar_yi_summons(self, ctx, name, *note):
        global hakkar_yi_summons
        message = await construct_args_message(note)
        await add_summoner_buffer(hakkar_yi_summons, name, message)
        await playback_message(ctx, 'Hakkar buff timer updated to:\n' + await calc_hakkar_msg())

    @commands.command(name='bb-sums-add', brief='Add user that is summoning to BB', help='Adds a BB summoner with cost/message - example: !bb-sums-add Thatguy 5g w/port')
    @commands.has_role('World Buff Coordinator')
    async def add_hakkar_bb_summons(self, ctx, name, *note):
        global hakkar_bb_summons
        message = await construct_args_message(note)
        await add_summoner_buffer(hakkar_bb_summons, name, message)
        await playback_message(ctx, 'Hakkar buff timer updated to:\n' + await calc_hakkar_msg())

    @commands.command(name='bvsf-sums-add', brief='Add user that is summoning to BVSF', help='Adds a BVSF summoner with cost/message - example: !swb-bvsf-sums-add Thatguy 5g w/port')
    @commands.has_role('World Buff Coordinator')
    async def add_bvsf_summons(self, ctx, name, *note):
        global bvsf_summons
        message = await construct_args_message(note)
        await add_summoner_buffer(bvsf_summons, name, message)
        await playback_message(ctx, 'BVSF buff timer updated to:\n' + await calc_bvsf_msg())

    @commands.command(name='dmt-sums-add', brief='Add user that is summoning to DMT', help='Adds a DMT summoner with cost/message - example: !dmt-sums-add Thatguy 5g w/port')
    @commands.has_role('World Buff Coordinator')
    async def add_dmt_summoner(self, ctx, name, *note):
        global dmt_summons
        message = await construct_args_message(note)
        await add_summoner_buffer(dmt_summons, name, message)
        await playback_message(ctx, 'DMT buff timer updated to:\n' + await calc_dmt_msg())

    @commands.command(name='dmf-sums-add', brief='Add user that is summoning to DMF', help='Adds a DMF summoner with cost/message - example: !dmf-sums-add Thatguy 5g w/port')
    @commands.has_role('World Buff Coordinator')
    async def add_dmf_summoner(self, ctx, name, *note):
        global dmf_summons
        message = await construct_args_message(note)
        await add_summoner_buffer(dmf_summons, name, message)
        await playback_message(ctx, 'DMF buff timer updated to:\n' + await calc_dmf_msg())

    @commands.command(name='aq-sums-add', brief='Add user that is summoning to AQ Gates', help='Adds a AQ Gates summoner with cost/message - example: !aq-sums-add Thatguy 5g w/port')
    @commands.has_role('World Buff Coordinator')
    async def add_aq_gates_summons(self, ctx, name, *note):
        global aq_summons
        message = await construct_args_message(note)
        await add_summoner_buffer(aq_summons, name, message)
        await playback_message(ctx, 'AQ Gates buff timer updated to:\n' + await calc_aq_msg())

    @commands.command(name='brm-sums-add', brief='Add user that is summoning to BRM', help='Adds a BRM summoner with cost/message - example: !brm-sums-add Thatguy 5g w/port')
    @commands.has_role('World Buff Coordinator')
    async def add_brm_summons(self, ctx, name, *note):
        global brm_summons
        message = await construct_args_message(note)
        await add_summoner_buffer(brm_summons, name, message)
        await playback_message(ctx, 'BRM buff timer updated to:\n' + await calc_brm_msg())


class SummonerRemoveCommands(commands.Cog, name='Removes the <name> of a summoner'):
    @commands.command(name='yi-sums-remove', brief='Remove user that was summoning to YI', help='Removes a YI summoner - example: !yi-sums-remove Thatguy')
    @commands.has_role('World Buff Coordinator')
    async def remove_hakkar_yi_summons(self, ctx, name):
        global hakkar_yi_summons
        if await remove_summoner_buffer_dropper(ctx, hakkar_yi_summons, name):
            await playback_message(ctx, 'Hakkar buff timer updated to:\n' + await calc_hakkar_msg())

    @commands.command(name='bb-sums-remove', brief='Remove user that was summoning to BB', help='Removes a BB summoner - example: !bb-sums-remove Thatguy')
    @commands.has_role('World Buff Coordinator')
    async def remove_hakkar_bb_summons(self, ctx, name):
        global hakkar_bb_summons
        if await remove_summoner_buffer_dropper(ctx, hakkar_bb_summons, name):
            await playback_message(ctx, 'Hakkar buff timer updated to:\n' + await calc_hakkar_msg())

    @commands.command(name='bvsf-sums-remove', brief='Remove user that was summoning to BVSF', help='Removes a BVSF summoner - example: !swb-bvsf-sums-remove Thatguy 5g w/port')
    @commands.has_role('World Buff Coordinator')
    async def remove_bvsf_summons(self, ctx, name):
        global bvsf_summons
        if await remove_summoner_buffer_dropper(ctx, bvsf_summons, name):
            await playback_message(ctx, 'BVSF buff timer updated to:\n' + await calc_bvsf_msg())

    @commands.command(name='dmt-sums-remove', brief='Remove user that was summoning to DMT', help='Removes a DMT summoner - example: !dmt-sums-remove Thatguy')
    @commands.has_role('World Buff Coordinator')
    async def remove_dmt_summoner(self, ctx, name):
        global dmt_summons
        if await remove_summoner_buffer_dropper(ctx, dmt_summons, name):
            await playback_message('DMT buff timer updated to:\n' + await calc_dmt_msg())

    @commands.command(name='dmf-sums-remove', brief='Remove user that was summoning to DMF', help='Removes a DMF summoner - example: !dmf-sums-remove Thatguy')
    @commands.has_role('World Buff Coordinator')
    async def remove_dmf_summoner(self, ctx, name):
        global dmf_summons
        if await remove_summoner_buffer_dropper(ctx, dmf_summons, name):
            if len(dmf_location) > 0 or len(dmf_summons) > 0:
                await playback_message(ctx, 'DMF buff timer updated to:\n' + await calc_dmf_msg())
            else:
                await playback_message(ctx, 'DMF buff timer removed')

    @commands.command(name='aq-sums-remove', brief='Remove user that was summoning to AQ Gates', help='Removes a AQ Gates summoner - example: !aq-sums-remove Thatguy')
    @commands.has_role('World Buff Coordinator')
    async def remove_aq_summons(self, ctx, name):
        global aq_summons
        if await remove_summoner_buffer_dropper(ctx, aq_summons, name):
            if len(aq_summons) > 0:
                await playback_message(ctx, 'AQ Gates buff timer updated to:\n' + await calc_aq_msg())
            else:
                await playback_message(ctx, 'AQ Gates buff timer removed')

    @commands.command(name='brm-sums-remove', brief='Remove user that was summoning to BRM', help='Removes a BRM summoner - example: !brm-sums-remove Thatguy')
    @commands.has_role('World Buff Coordinator')
    async def remove_brm_summons(self, ctx, name):
        global brm_summons
        if await remove_summoner_buffer_dropper(ctx, brm_summons, name):
            if len(brm_summons) > 0:
                await playback_message(ctx, 'BRM buff timer updated to:\n' + await calc_brm_msg())
            else:
                await playback_message(ctx, 'BRM buff timer removed')


class DMTBuffCommands(commands.Cog, name = 'Adds the <name> of a DMT buff seller and the [note] which may contain cost or other info or Removes the <name> of the DMT buffer'):
    @commands.command(name='dmt-buffs-add', brief='Add user that is offering DMT buffs', help='Adds a DMT buffer with cost/message - example: !dmt-buffs-add Thatguy 5g w/port')
    @commands.has_role('World Buff Coordinator')
    async def add_dmt_buffs(self, ctx, name, *note):
        global dmt_buffs
        message = await construct_args_message(note)
        await add_summoner_buffer(dmt_buffs, name, message)
        await playback_message(ctx, 'DMT buff timer updated to:\n' + await calc_dmt_msg())

    @commands.command(name='dmt-buffs-remove', brief='Remove user that was offering DMT buffs', help='Removes a DMT buffer - example: !dmt-sums-remove Thatguy')
    @commands.has_role('World Buff Coordinator')
    async def remove_dmt_buffs(self, ctx, name):
        global dmt_buffs
        if await remove_summoner_buffer_dropper(ctx, dmt_buffs, name):
            await playback_message(ctx, 'DMT buff timer updated to:\n' + await calc_dmt_msg())


class DMFBuffCommands(commands.Cog, name = 'Specifies the [location] of the DMF (Elwynn Forest or Mulgore) - specifying no location will hide the message when no summoners are present'):
    @commands.command(name='dmf-loc', brief='Sets the location of the DMF', help='Sets the location of the DMF - example: !dmf-loc Elwynn Forest')
    @commands.has_role('World Buff Coordinator')
    async def set_dmf_location(self, ctx, *location):
        global dmf_location
        dmf_location = await construct_args_message(location)
        await post_in_world_buffs_chat_channel()
        if len(dmf_location) > 0 or len(dmf_summons) > 0:
            await playback_message(ctx, 'DMF buff timer updated to:\n' + await calc_dmf_msg())
        else:
            await playback_message(ctx, 'DMF buff timer removed')


class ServerMaintenanceCommands(commands.Cog, name = 'Specifies the maintenance or server status [message] - specifying no message will hide the message'):
    @commands.command(name='server-status', brief='Set a message to display in the server status section', help='Sets a message to display in the server status section - example: !server-status server restart @10:00am')
    @commands.has_role('World Buff Coordinator')
    async def set_maintenance_message(self, ctx, *message):
        global server_maintenance
        server_maintenance = await construct_args_message(message)
        await post_in_world_buffs_chat_channel()
        if len(server_maintenance) > 0:
            await playback_message(ctx, 'Server status message updated to:\n' + await get_maintenance())
        else:
            await playback_message(ctx, 'Server status message removed')


class GriefingCommands(commands.Cog, name = 'Specifies the ally sighting / griefing [message] - specifying no message will hide the message'):
    @commands.command(name='ally', brief='Set a message to display in the ally warning section', help='Sets a message to display in the ally warning section - example: !ally Ally sighting at BRM')
    @commands.has_role('World Buff Coordinator')
    async def set_alliance_message(self, ctx, *message):
        global alliance
        alliance = await construct_args_message(message)
        await post_in_world_buffs_chat_channel()
        if len(alliance) > 0:
            await playback_message(ctx, 'Alliance warning message updated to:\n' + await get_alliance())
        else:
            await playback_message(ctx, 'Alliance warning message removed')


class ExtraMessageCommands(commands.Cog, name = 'Specifies an additional footer [message] - specifying no message will hide the message'):
    @commands.command(name='extra-msg', brief='Set a message to display in the extra message/footer section', help='Sets a message to display in the extra message/footer section - example: !extra-msg Ally sighting at BRM')
    @commands.has_role('World Buff Coordinator')
    async def set_extra_footer_message(self, ctx, *message):
        global extra_message
        extra_message = await construct_args_message(message)
        await post_in_world_buffs_chat_channel()
        if len(extra_message) > 0:
            await playback_message(ctx, 'Extra footer message updated to:\n' + await get_extra_message())
        else:
            await playback_message(ctx, 'Extra footer message removed')


async def get_buff_times():
    await check_for_bvsf_updates()
    message = await get_timestamp()
    message = message + await get_maintenance()
    message = message + await calc_rend_msg() + '\n'
    message = message + await calc_ony_msg() + '\n'
    message = message + await calc_nef_msg() + '\n'
    message = message + await calc_hakkar_msg() + '\n'
    message = message + await calc_bvsf_msg() + '\n'
    message = message + await calc_dmt_msg() + '\n'
    message = message + await calc_aq_msg()
    message = message + await calc_brm_msg()
    message = message + await calc_dmf_msg()
    message = message + await get_alliance()
    message = message + await get_extra_message()
    return message

async def get_timestamp():
    local_time = await get_local_time()
    return '**Updated as of ' + datetime.strftime(local_time, '%Y-%m-%d at %#I:%M%p').lower() + ' ST**\n\n'

async def get_maintenance():
    if len(server_maintenance) > 0:
        return ':tools: **' + server_maintenance + '** :tools:\n\n'
    else:
        return ''

async def get_alliance():
    if len(alliance) > 0:
        return ':warning:  ' + alliance + '\n'
    else:
        return ''

async def get_extra_message():
    if len(extra_message) > 0:
        return '\n' + extra_message + '\n'
    else:
        return ''

async def calc_rend_msg():
    message = ':japanese_ogre:  Rend --- ' + rend_time
    message = message + await droppers_msg(rend_drops, rend_time)
    return message

async def calc_ony_msg():
    message = ':dragon:  Ony --- ' + ony_time
    message = message + await droppers_msg(ony_drops, ony_time)
    return message

async def calc_nef_msg():
    message = ':dragon_face:  Nef --- ' + nef_time
    message = message + await droppers_msg(nef_drops, nef_time)
    return message

async def calc_hakkar_msg():
    message = ':heartpulse:  Hakkar  --- '
    if len(hakkar_drops) > 0:
        message = message + await droppers_msg(hakkar_drops, '')
    else:
        message = message + '?:??'
    if len(hakkar_yi_summons) > 0:
        message = message + '  --  ' + await summoners_buffers_msg(hakkar_yi_summons, 'YI summons')
    if len(hakkar_bb_summons) > 0:
        message = message + '  --  ' + await summoners_buffers_msg(hakkar_bb_summons, 'BB summons')
    return message

async def calc_bvsf_msg():
    if await validate_time_format(bvsf_time):
        next_time_1 = await calculate_next_flower(bvsf_time)
        next_time_2 = await calculate_next_flower(next_time_1)
        message = ':wilted_rose:  BVSF --- ' + bvsf_time + ' -> ' + next_time_1 + ' -> ' + next_time_2
    else:
        message = ':wilted_rose:  BVSF --- ' + bvsf_time
    if len(bvsf_summons) > 0:
        message = message + '  --  ' + await summoners_buffers_msg(bvsf_summons)
    return message

async def calc_dmt_msg():
    message = await summoners_buffers_msg(dmt_buffs, 'DM buffs')
    if len(dmt_summons) > 0:
        if len(message) > 0:
            message = message + '  --  ' + await summoners_buffers_msg(dmt_summons)
        else:
            message = await summoners_buffers_msg(dmt_summons)
    if len(message) == 0:
        message = 'None available at this time'
    message = ':crown:  DMT --- ' + message
    return message

async def calc_aq_msg():
    message = ''
    if len(aq_summons) > 0:
        message = ':bug:  AQ Gates --- ' + await summoners_buffers_msg(aq_summons) + '\n'
    return message

async def calc_brm_msg():
    message = ''
    if len(brm_summons) > 0:
        message = ':mountain:  BRM --- ' + await summoners_buffers_msg(brm_summons) + '\n'
    return message

async def calc_dmf_msg():
    if len(dmf_location) == 0 and len(dmf_summons) == 0:
        return ''
    message = ''
    if len(dmf_location) > 0:
        message = ':circus_tent:  DMF (' + dmf_location + ') --- '
    else:
        message = ':circus_tent:  DMF --- '
    if len(dmf_summons) > 0:
        message = message + await summoners_buffers_msg(dmf_summons)
    else:
        message = message + ' No summons available at this time'
    message = message + '\n'
    return message

async def check_for_bvsf_updates():
    global bvsf_time
    if not await validate_time_format(bvsf_time):
        return;
    local_time = await get_local_time()
    bvsf_date_time = datetime.strptime(bvsf_time, '%I:%M%p')
    new_time = local_time.replace(hour=bvsf_date_time.hour, minute=bvsf_date_time.minute)
    while local_time > new_time:
        new_time = new_time + timedelta(minutes=25)
    bvsf_time = datetime.strftime(new_time, '%-I:%M%p').lower()

async def get_local_time():
    utc = timezone('UTC')
    now = utc.localize(datetime.utcnow())
    local_time = now.astimezone(timezone('US/Eastern'))
    return local_time

async def droppers_msg(droppers, next_drop_time):
    message = ''
    for drop in droppers:
        if drop.time == next_drop_time:
            message = message + ' (**' + drop.name + '**)'
        else:
            message = message + ' (' + drop.time + ' - **' + drop.name + '**)'
    return message

async def summoners_buffers_msg(summoners, message_ending = 'summons'):
    message = ''
    if len(summoners) > 0:
        message = message + 'Whisper '
        for index in range(len(summoners)):
            summoner = summoners[index]
            if index > 0:
                message = message + '  |  '
            message = message + ' **' + summoner.name + '** '
            if len(summoner.msg) > 0:
                message = message + '(' + summoner.msg + ') '
        message = message + ' \'inv\' for {0}'.format(message_ending)
    return message

async def add_dropper(droppers, name, time):
    for drop in droppers:
        if drop.name == name.title():
            drop.time = time
            return

    dropper = Dropper(time, name.title())
    droppers.append(dropper)

async def add_summoner_buffer(summoners_buffers, name, message):
    for summon_buff in summoners_buffers:
        if summon_buff.name == name.title():
            summon_buff.msg = message
            await post_in_world_buffs_chat_channel()
            return

    summoner_buffer = SummonerBuffer(name.title(), message)
    summoners_buffers.append(summoner_buffer)
    await post_in_world_buffs_chat_channel()

async def remove_summoner_buffer_dropper(ctx, summoners_buffers_droppers, name):
    for summon_buff_drop in summoners_buffers_droppers:
        if summon_buff_drop.name == name.title():
            summoners_buffers_droppers.remove(summon_buff_drop)
            await post_in_world_buffs_chat_channel()
            return True

    await ctx.send('Name **{0}** not found - nothing to remove'.format(name))
    return False

async def construct_args_message(args):
    message = ''
    for index in range(len(args)):
        if index > 0:
            message = message + ' '
        message = message + args[index]
    return message

async def calculate_next_flower(time_str):
    if not await validate_time_format(time_str):
        return;
    time = datetime.strptime(time_str, '%I:%M%p')
    new_time = time + timedelta(minutes=25)
    return datetime.strftime(new_time, '%-I:%M%p').lower()

async def validate_time_format(time):
    valid = re.search('^[0-2]?[0-9]:[0-5][0-9][a,p]m$', time)
    return valid

async def playback_message(ctx, message):
    if (playback_updates):
        await ctx.send(message)

async def post_in_world_buffs_chat_channel():
    channel = bot.get_channel(CHANNEL_ID)
    messages = await channel.history(limit = 1).flatten()
    if len(messages) > 0 and messages[0].author == bot.user:
        message = await channel.fetch_message(messages[0].id)
        await message.edit(content = await get_buff_times())
    else:
        await channel.send(await get_buff_times())


bot.add_cog(BuffAvailTimeCommands(bot))
bot.add_cog(BVSFBuffCommands(bot))
bot.add_cog(BuffDropAddCommands(bot))
bot.add_cog(BuffDropRemoveCommands(bot))
bot.add_cog(SummonerAddCommands(bot))
bot.add_cog(SummonerRemoveCommands(bot))
bot.add_cog(DMTBuffCommands(bot))
bot.add_cog(DMFBuffCommands(bot))
bot.add_cog(ServerMaintenanceCommands(bot))
bot.add_cog(GriefingCommands(bot))
bot.add_cog(ExtraMessageCommands(bot))

bot.run(TOKEN)

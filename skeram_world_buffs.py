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
WORLD_BUFF_CHANNEL_ID = int(os.getenv('WORLD_BUFF_CHANNEL_ID'))
WBC_CHANNEL_ID = int(os.getenv('WBC_CHANNEL_ID'))
WORLD_BUFF_COORDINATOR_ROLE_ID = int(os.getenv('WORLD_BUFF_COORDINATOR_ROLE_ID'))
WORLD_BUFF_SELLER_ROLE_ID = int(os.getenv('WORLD_BUFF_SELLER_ROLE_ID'))
MASTER_ID = int(os.getenv('MASTER_ID'))

bot = commands.Bot(command_prefix='!swb-', case_insensitive=True)
bot.remove_command('help')


class Dropper:
    def __init__(self, t='?:??', n='NA', a=''):
        self.time = t
        self.name = n
        self.author = a

class SummonerBuffer:
    def __init__(self, n='?:??', m='NA', a=''):
        self.name = n
        self.msg = m
        self.author = a


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
naxx_summons = []
aq_summons = []
brm_summons = []
dmf_location = ''
dmf_summons = []
alliance = ''
extra_message = ''



@bot.command(name="help", description="Shows all available commands")
async def help(ctx):
    helptext = "```"
    helptext += '{0.command_prefix}{1.qualified_name} {1.signature}\n  {1.description}\n\n'.format(bot, bot.get_command('help'))
    for cog in bot.cogs:
        commands = ''
        cog_obj = bot.get_cog(cog)
        for command in cog_obj.get_commands():
            commands += '\n{0.command_prefix}{1.qualified_name} {1.signature}'.format(bot, command)
        helptext += '{0}\n  {1.qualified_name}\n\n'.format(commands, cog_obj)
    helptext += "```"
    await ctx.send(helptext)

@bot.command(name="playback", description="Updates if bot should print out when changes occur [on|off]")
async def playback(ctx, status):
    if (ctx.message.author.id != MASTER_ID):
        raise commands.CommandNotFound()
        return
    global playback_updates
    if status.lower() == 'on':
        playback_updates = True
    else:
        playback_updates = False
    await ctx.send('Playback is ' + ('enabled' if status == 'on' else 'disabled'))

@bot.command(name="clear-all-data-confirm", description="Purges all saved data")
async def clear_all_data(ctx):
    if (ctx.message.author.id != MASTER_ID):
        raise commands.CommandNotFound()
        return
    world_buff_channel = bot.get_channel(WORLD_BUFF_CHANNEL_ID)
    messages = await world_buff_channel.history(limit = 1).flatten()
    if len(messages) > 0 and messages[0].author == bot.user:
        message = await world_buff_channel.fetch_message(messages[0].id)
        await ctx.send('**Data cleared...**\nPrevious Message:\n' + message.content)
    global server_maintenance
    server_maintenance = ''
    global rend_time
    global rend_drops
    rend_time = '?:??'
    rend_drops = []
    global ony_time
    global ony_drops
    ony_time = '?:??'
    ony_drops = []
    global nef_time
    global nef_drops
    nef_time = '?:??'
    nef_drops = []
    global hakkar_drops
    global hakkar_yi_summons
    global hakkar_bb_summons
    hakkar_drops = []
    hakkar_yi_summons= []
    hakkar_bb_summons = []
    global bvsf_time
    global bvsf_summons
    bvsf_time = "?:??"
    bvsf_summons = []
    global dmt_buffs
    global dmt_summons
    dmt_buffs = []
    dmt_summons = []
    global naxx_summons
    naxx_summons = []
    global aq_summons
    aq_summons = []
    global brm_summons
    brm_summons = []
    global dmf_location
    dmf_location = ''
    global dmf_summons
    dmf_summons = []
    global alliance
    alliance = ''
    global extra_message
    extra_message = ''
    await post_in_world_buffs_chat_channel()
    await ctx.send('All data cleared')

@bot.command(name="mockup-data-confirm", description="Populates all elements of the message with dummy data")
async def mockup_data(ctx):
    if (ctx.message.author.id != MASTER_ID):
        raise commands.CommandNotFound()
        return
    global server_maintenance
    server_maintenance = 'SERVER IS UP'
    global rend_time
    global rend_drops
    rend_time = '3:00pm'
    await add_dropper_no_post(rend_drops, 'Renddropper', '3:00pm')
    await add_dropper_no_post(rend_drops, 'Nextdropper', '6:00pm')
    global ony_time
    global ony_drops
    ony_time = 'OPEN'
    await add_dropper_no_post(ony_drops, 'Onydropper', '8:00pm')
    global nef_time
    global nef_drops
    nef_time = '7:45pm'
    global hakkar_drops
    global hakkar_yi_summons
    global hakkar_bb_summons
    await add_dropper_no_post(hakkar_drops, 'Hakkardrop', '7:00pm')
    await add_dropper_no_post(hakkar_drops, 'Hakkarnotdrop', '9:15pm')
    await add_summoner_buffer_no_post(hakkar_yi_summons, 'YIsums', ['5g'])
    await add_summoner_buffer_no_post(hakkar_yi_summons, 'YIsummer', ['4g w/port'])
    await add_summoner_buffer_no_post(hakkar_bb_summons, 'BBsums', [''])
    global bvsf_time
    global bvsf_summons
    #bvsf_time = '4:35pm'
    await add_summoner_buffer_no_post(bvsf_summons, 'Whosums', ['5g'])
    global dmt_buffs
    global dmt_summons
    await add_summoner_buffer_no_post(dmt_buffs, 'Mybuffs', ['7g w/port and summons'])
    await add_summoner_buffer_no_post(dmt_buffs, 'Dmtbuffs', ['5g'])
    await add_summoner_buffer_no_post(dmt_summons, 'Datsums', ['8g'])
    global naxx_summons
    await add_summoner_buffer_no_post(naxx_summons, 'naxxsums', ['7g'])
    global aq_summons
    await add_summoner_buffer_no_post(aq_summons, 'aqSums', ['3g'])
    global brm_summons
    await add_summoner_buffer_no_post(brm_summons, 'brmsums', ['8g'])
    global dmf_location
    dmf_location = 'Mulgore'
    global dmf_summons
    await add_summoner_buffer_no_post(dmf_summons, 'dmfsums', ['10g'])
    global alliance
    alliance = 'ALLY everywhere - dont die'
    global extra_message
    extra_message = 'Extra message for ........'
    await post_in_world_buffs_chat_channel()
    await ctx.send('Data mocked up')


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound) or isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send('**Unknown command entered or parameters are missing** - a list of commands and usage can be found using !swb-help')
        return
    if isinstance(error, commands.errors.MissingRole) or isinstance(error, commands.errors.MissingAnyRole):
        await ctx.send('**Missing role to execute this command**')
        return
    raise error

@bot.event
async def on_ready():
    world_buff_channel = bot.get_channel(WORLD_BUFF_CHANNEL_ID)
    wbc_channel = bot.get_channel(WBC_CHANNEL_ID)
    messages = await world_buff_channel.history(limit = 1).flatten()
    if len(messages) > 0 and messages[0].author == bot.user:
        message = await world_buff_channel.fetch_message(messages[0].id)
        message_content = message.content
        populate_success = await populate_data_from_message(message_content)

        new_message = await get_buff_times()
        if populate_success:
            await wbc_channel.send('**Bot restarted....**\nworld-buff-times message reposted')
        else:
            await wbc_channel.send('**Bot restarted....**\nExisting Message:\n{0}\n\n\n'.format(message_content))
            await wbc_channel.send('New Message:\n{0}\n\nSome discrepencies may exist in existing vs new message after restart, please verify'.format(new_message))
        await message.edit(content = new_message)
    else:
        await wbc_channel.send('**Bot restarted....**\nNo exising message found, all data cleared')

@bot.event
async def on_message(message):
    if message.channel.id != WBC_CHANNEL_ID:
        # only read messages from designated channel
        return
    await bot.process_commands(message)


class BuffAvailTimeCommands(commands.Cog, name='Specifies the <time> when the buff is open/off CD'):
    @commands.command(name='rend', brief='Set time for when rend is open/off CD', help='Sets the next available time rend buff is open - example: !rend 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_rend_time(self, ctx, time):
        global rend_time
        rend_time = time
        await post_in_world_buffs_chat_channel()
        await playback_message(ctx, 'Rend buff timer updated to:\n' + await calc_rend_msg())

    @commands.command(name='ony', brief='Set time for when ony is open/off CD', help='Sets the next available time ony buff is open - example: !ony 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_ony_time(self, ctx, time):
        global ony_time
        ony_time = time
        await post_in_world_buffs_chat_channel()
        await playback_message(ctx, 'Ony buff timer updated to:\n' + await calc_ony_msg())

    @commands.command(name='nef', brief='Set time for when nef is open/off CD', help='Sets the next available time nef buff is open - example: !nef 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_nef_time(self, ctx, time):
        global nef_time
        nef_time = time
        await post_in_world_buffs_chat_channel()
        await playback_message(ctx, 'Nef buff timer updated to:\n' + await calc_nef_msg())


class BVSFBuffCommands(commands.Cog, name = 'Sets the next <time> the BVSF flower should be up or clears it'):
    @commands.command(name='bvsf', brief='Set time when BVSF is up', help='Sets the next time bvsf flower buff is up - example: !bvsf 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_bvsf_time(self, ctx, time):
        global bvsf_time
        if await validate_time_format(time):
            bvsf_time = time
            await post_in_world_buffs_chat_channel()
            await playback_message(ctx, 'BVSF buff timer updated to:\n' + await calc_bvsf_msg())
        else:
            await playback_invalid_time_message(ctx)

    @commands.command(name='bvsf-clear', brief='Clears BVSF time, sets to ?:??', help='Sets the BVSF time to ?:?? - example: !bvsf-clear')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def clear_bvsf_time(self, ctx):
        global bvsf_time
        bvsf_time = '?:??'
        await post_in_world_buffs_chat_channel()
        await playback_message(ctx, 'BVSF buff timer updated to:\n' + await calc_bvsf_msg())


class BuffDropAddCommands(commands.Cog, name='Adds the <name> of a buff dropper and the planned <time>'):
    @commands.command(name='rend-drop', aliases=['rend-drop-add'], brief='Add user that will drop rend along with drop time', help='Sets a rend confirmed dropper - example: !rend-drop Thatguy 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_rend_dropper(self, ctx, name, time):
        global rend_drops
        if await validate_time_format(time):
            await add_dropper(rend_drops, name, time)
            await playback_message(ctx, 'Rend buff timer updated to:\n' + await calc_rend_msg())
        else:
            await playback_invalid_time_message(ctx)

    @commands.command(name='ony-drop', aliases=['ony-drop-add'], brief='Add user that will drop ony along with drop time', help='Sets a ony confirmed dropper - example: !ony-drop Thatguy 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_ony_dropper(self, ctx, name, time):
        global ony_drops
        if await validate_time_format(time):
            await add_dropper(ony_drops, name, time)
            await playback_message(ctx, 'Ony buff timer updated to:\n' + await calc_ony_msg())
        else:
            await playback_invalid_time_message(ctx)

    @commands.command(name='nef-drop', aliases=['nef-drop-add'], brief='Add user that will drop nef along with drop time', help='Sets a nef confirmed dropper - example: !nef-drop Thatguy 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_nef_dropper(self, ctx, name, time):
        global nef_drops
        if await validate_time_format(time):
            await add_dropper(nef_drops, name, time)
            await playback_message(ctx, 'Nef buff timer updated to:\n' + await calc_nef_msg())
        else:
            await playback_invalid_time_message(ctx)

    @commands.command(name='hakkar-drop', aliases=['hakkar-drop-add'], brief='Add user that will drop hakkar along with drop time', help='Sets a hakkar confirmed dropper - example: !hakkar-drop Thatguy 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_hakkar_dropper(self, ctx, name, time):
        global hakkar_drops
        if await validate_time_format(time):
            await add_dropper(hakkar_drops, name, time)
            await playback_message(ctx, 'Hakkar buff timer updated to:\n' + await calc_hakkar_msg())
        else:
            await playback_invalid_time_message(ctx)


class BuffDropRemoveCommands(commands.Cog, name='Removes the <name> of a buff dropper'):
    @commands.command(name='rend-drop-remove', brief='Remove user dropping rend', help='Removes a rend confirmed dropper - example: !rend-drop-remove Thatguy')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def remove_rend_dropper(self, ctx, name):
        global rend_drops
        if await remove_summoner_buffer_dropper(ctx, rend_drops, name):
            await playback_message(ctx, 'Rend buff timer updated to:\n' + await calc_rend_msg())

    @commands.command(name='ony-drop-remove', brief='Remove user dropping ony', help='Removes a ony confirmed dropper - example: !ony-drop-remove Thatguy')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def remove_ony_dropper(self, ctx, name):
        global ony_drops
        if await remove_summoner_buffer_dropper(ctx, ony_drops, name):
            await playback_message(ctx, 'Ony buff timer updated to:\n' + await calc_ony_msg())

    @commands.command(name='nef-drop-remove', brief='Remove user dropping nef', help='Removes a nef confirmed dropper - example: !nef-drop-remove Thatguy')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def remove_nef_dropper(self, ctx, name):
        global nef_drops
        if await remove_summoner_buffer_dropper(ctx, nef_drops, name):
            await playback_message(ctx, 'Nef buff timer updated to:\n' + await calc_nef_msg())

    @commands.command(name='hakkar-drop-remove', brief='Remove user dropping hakkar', help='Removes a hakkar confirmed dropper - example: !hakkar-drop-remove Thatguy')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def remove_hakkar_dropper(self, ctx, name):
        global hakkar_drops
        if await remove_summoner_buffer_dropper(ctx, hakkar_drops, name):
            await playback_message(ctx, 'Hakkar buff timer updated to:\n' + await calc_hakkar_msg())


class SummonerAddCommands(commands.Cog, name='Adds the <name> of a summoner and the [note] which may contain cost or other info'):
    @commands.command(name='yi-sums-add', aliases=['yi-sums'], brief='Add user that is summoning to YI', help='Adds a YI summoner with cost/message - example: !yi-sums-add Thatguy 5g w/port')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def add_hakkar_yi_summons(self, ctx, name, *note):
        global hakkar_yi_summons
        await add_summoner_buffer(hakkar_yi_summons, name, note, ctx.message.author.id)
        await playback_message(ctx, 'Hakkar buff timer updated to:\n' + await calc_hakkar_msg())

    @commands.command(name='bb-sums-add', aliases=['bb-sums'], brief='Add user that is summoning to BB', help='Adds a BB summoner with cost/message - example: !bb-sums-add Thatguy 5g w/port')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def add_hakkar_bb_summons(self, ctx, name, *note):
        global hakkar_bb_summons
        await add_summoner_buffer(hakkar_bb_summons, name, note, ctx.message.author.id)
        await playback_message(ctx, 'Hakkar buff timer updated to:\n' + await calc_hakkar_msg())

    @commands.command(name='bvsf-sums-add', aliases=['bvsf-sums'], brief='Add user that is summoning to BVSF', help='Adds a BVSF summoner with cost/message - example: !swb-bvsf-sums-add Thatguy 5g w/port')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def add_bvsf_summons(self, ctx, name, *note):
        global bvsf_summons
        await add_summoner_buffer(bvsf_summons, name, note, ctx.message.author.id)
        await playback_message(ctx, 'BVSF buff timer updated to:\n' + await calc_bvsf_msg())

    @commands.command(name='dmt-sums-add', aliases=['dmt-sums'], brief='Add user that is summoning to DMT', help='Adds a DMT summoner with cost/message - example: !dmt-sums-add Thatguy 5g w/port')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def add_dmt_summoner(self, ctx, name, *note):
        global dmt_summons
        await add_summoner_buffer(dmt_summons, name, note, ctx.message.author.id)
        await playback_message(ctx, 'DMT buff timer updated to:\n' + await calc_dmt_msg())

    @commands.command(name='dmf-sums-add', aliases=['dmf-sums'], brief='Add user that is summoning to DMF', help='Adds a DMF summoner with cost/message - example: !dmf-sums-add Thatguy 5g w/port')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def add_dmf_summoner(self, ctx, name, *note):
        global dmf_summons
        await add_summoner_buffer(dmf_summons, name, note, ctx.message.author.id)
        await playback_message(ctx, 'DMF buff timer updated to:\n' + await calc_dmf_msg())

    @commands.command(name='naxx-sums-add', aliases=['naxx-sums', 'nax-sums-add', 'nax-sums'], brief='Add user that is summoning to Naxx', help='Adds a Naxx summoner with cost/message - example: !naxx-sums-add Thatguy 5g w/port')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def add_naxx_summons(self, ctx, name, *note):
        global naxx_summons
        await add_summoner_buffer(naxx_summons, name, note, ctx.message.author.id)
        await playback_message(ctx, 'Naxx buff timer updated to:\n' + await calc_naxx_msg())

    @commands.command(name='aq-sums-add', aliases=['aq-sums'], brief='Add user that is summoning to AQ Gates', help='Adds a AQ Gates summoner with cost/message - example: !aq-sums-add Thatguy 5g w/port')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def add_aq_gates_summons(self, ctx, name, *note):
        global aq_summons
        await add_summoner_buffer(aq_summons, name, note, ctx.message.author.id)
        await playback_message(ctx, 'AQ Gates buff timer updated to:\n' + await calc_aq_msg())

    @commands.command(name='brm-sums-add', aliases=['brm-sums'], brief='Add user that is summoning to BRM', help='Adds a BRM summoner with cost/message - example: !brm-sums-add Thatguy 5g w/port')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def add_brm_summons(self, ctx, name, *note):
        global brm_summons
        await add_summoner_buffer(brm_summons, name, note, ctx.message.author.id)
        await playback_message(ctx, 'BRM buff timer updated to:\n' + await calc_brm_msg())


class SummonerRemoveCommands(commands.Cog, name='Removes the <name> of a summoner'):
    @commands.command(name='yi-sums-remove', brief='Remove user that was summoning to YI', help='Removes a YI summoner - example: !yi-sums-remove Thatguy')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def remove_hakkar_yi_summons(self, ctx, name):
        global hakkar_yi_summons
        if await has_rights_to_remove(hakkar_yi_summons, name, ctx.message.author):
            if await remove_summoner_buffer_dropper(ctx, hakkar_yi_summons, name):
                await playback_message(ctx, 'Hakkar buff timer updated to:\n' + await calc_hakkar_msg())

    @commands.command(name='bb-sums-remove', brief='Remove user that was summoning to BB', help='Removes a BB summoner - example: !bb-sums-remove Thatguy')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def remove_hakkar_bb_summons(self, ctx, name):
        global hakkar_bb_summons
        if await has_rights_to_remove(hakkar_bb_summons, name, ctx.message.author):
            if await remove_summoner_buffer_dropper(ctx, hakkar_bb_summons, name):
                await playback_message(ctx, 'Hakkar buff timer updated to:\n' + await calc_hakkar_msg())

    @commands.command(name='bvsf-sums-remove', brief='Remove user that was summoning to BVSF', help='Removes a BVSF summoner - example: !swb-bvsf-sums-remove Thatguy 5g w/port')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def remove_bvsf_summons(self, ctx, name):
        global bvsf_summons
        if await has_rights_to_remove(bvsf_summons, name, ctx.message.author):
            if await remove_summoner_buffer_dropper(ctx, bvsf_summons, name):
                await playback_message(ctx, 'BVSF buff timer updated to:\n' + await calc_bvsf_msg())

    @commands.command(name='dmt-sums-remove', brief='Remove user that was summoning to DMT', help='Removes a DMT summoner - example: !dmt-sums-remove Thatguy')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def remove_dmt_summoner(self, ctx, name):
        global dmt_summons
        if await has_rights_to_remove(dmt_summons, name, ctx.message.author):
            if await remove_summoner_buffer_dropper(ctx, dmt_summons, name):
                await playback_message(ctx, 'DMT buff timer updated to:\n' + await calc_dmt_msg())

    @commands.command(name='dmf-sums-remove', brief='Remove user that was summoning to DMF', help='Removes a DMF summoner - example: !dmf-sums-remove Thatguy')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def remove_dmf_summoner(self, ctx, name):
        global dmf_summons
        if await has_rights_to_remove(dmf_summons, name, ctx.message.author):
            if await remove_summoner_buffer_dropper(ctx, dmf_summons, name):
                if len(dmf_location) > 0 or len(dmf_summons) > 0:
                    await playback_message(ctx, 'DMF buff timer updated to:\n' + await calc_dmf_msg())
                else:
                    await playback_message(ctx, 'DMF buff timer removed')

    @commands.command(name='naxx-sums-remove', aliases=['nax-sums-remove'], brief='Remove user that was summoning to Naxx', help='Removes a Naxx summoner - example: !naxx-sums-remove Thatguy')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def remove_naxx_summons(self, ctx, name):
        global naxx_summons
        if await has_rights_to_remove(naxx_summons, name, ctx.message.author):
            if await remove_summoner_buffer_dropper(ctx, naxx_summons, name):
                if len(naxx_summons) > 0:
                    await playback_message(ctx, 'Naxx buff timer updated to:\n' + await calc_naxx_msg())
                else:
                    await playback_message(ctx, 'Naxx buff timer removed')

    @commands.command(name='aq-sums-remove', brief='Remove user that was summoning to AQ Gates', help='Removes a AQ Gates summoner - example: !aq-sums-remove Thatguy')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def remove_aq_summons(self, ctx, name):
        global aq_summons
        if await has_rights_to_remove(aq_summons, name, ctx.message.author):
            if await remove_summoner_buffer_dropper(ctx, aq_summons, name):
                if len(aq_summons) > 0:
                    await playback_message(ctx, 'AQ Gates buff timer updated to:\n' + await calc_aq_msg())
                else:
                    await playback_message(ctx, 'AQ Gates buff timer removed')

    @commands.command(name='brm-sums-remove', brief='Remove user that was summoning to BRM', help='Removes a BRM summoner - example: !brm-sums-remove Thatguy')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def remove_brm_summons(self, ctx, name):
        global brm_summons
        if await has_rights_to_remove(brm_summons, name, ctx.message.author):
            if await remove_summoner_buffer_dropper(ctx, brm_summons, name):
                if len(brm_summons) > 0:
                    await playback_message(ctx, 'BRM buff timer updated to:\n' + await calc_brm_msg())
                else:
                    await playback_message(ctx, 'BRM buff timer removed')


class DMTBuffCommands(commands.Cog, name = 'Adds the <name> of a DMT buff seller and the [note] which may contain cost or other info or Removes the <name> of the DMT buffer'):
    @commands.command(name='dmt-buffs-add', aliases=['dmt-buffs'], brief='Add user that is offering DMT buffs', help='Adds a DMT buffer with cost/message - example: !dmt-buffs-add Thatguy 5g w/port')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def add_dmt_buffs(self, ctx, name, *note):
        global dmt_buffs
        await add_summoner_buffer(dmt_buffs, name, note, ctx.message.author.id)
        await playback_message(ctx, 'DMT buff timer updated to:\n' + await calc_dmt_msg())

    @commands.command(name='dmt-buffs-remove', brief='Remove user that was offering DMT buffs', help='Removes a DMT buffer - example: !dmt-sums-remove Thatguy')
    @commands.has_any_role(WORLD_BUFF_COORDINATOR_ROLE_ID, WORLD_BUFF_SELLER_ROLE_ID)
    async def remove_dmt_buffs(self, ctx, name):
        global dmt_buffs
        if await has_rights_to_remove(dmt_buffs, name, ctx.message.author):
            if await remove_summoner_buffer_dropper(ctx, dmt_buffs, name):
                await playback_message(ctx, 'DMT buff timer updated to:\n' + await calc_dmt_msg())


class DMFBuffCommands(commands.Cog, name = 'Specifies the [location] of the DMF (Elwynn Forest or Mulgore) - specifying no location will hide the message when no summoners are present'):
    @commands.command(name='dmf-loc', brief='Sets the location of the DMF', help='Sets the location of the DMF - example: !dmf-loc Elwynn Forest')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_dmf_location(self, ctx, *location):
        global dmf_location
        dmf_location = (await construct_args_message(location)).title()
        await post_in_world_buffs_chat_channel()
        if len(dmf_location) > 0 or len(dmf_summons) > 0:
            await playback_message(ctx, 'DMF buff timer updated to:\n' + await calc_dmf_msg())
        else:
            await playback_message(ctx, 'DMF buff timer removed')


class ServerMaintenanceCommands(commands.Cog, name = 'Specifies the maintenance or server status [message] - specifying no message will hide the message'):
    @commands.command(name='server-status', brief='Set a message to display in the server status section', help='Sets a message to display in the server status section - example: !server-status server restart @10:00am')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
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
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
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
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
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
    message += await get_maintenance()
    message += await calc_rend_msg() + '\n'
    message += await calc_ony_msg() + '\n'
    message += await calc_nef_msg() + '\n'
    message += await calc_hakkar_msg() + '\n'
    message += await calc_bvsf_msg() + '\n'
    message += await calc_dmt_msg() + '\n'
    message += await calc_naxx_msg()
    message += await calc_aq_msg()
    message += await calc_brm_msg()
    message += await calc_dmf_msg()
    message += await get_alliance()
    message += await get_extra_message()
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
    message += await droppers_msg(rend_drops, rend_time)
    return message

async def calc_ony_msg():
    message = ':dragon:  Ony --- ' + ony_time
    message += await droppers_msg(ony_drops, ony_time)
    return message

async def calc_nef_msg():
    message = ':dragon_face:  Nef --- ' + nef_time
    message += await droppers_msg(nef_drops, nef_time)
    return message

async def calc_hakkar_msg():
    message = ':heartpulse:  Hakkar --- '
    if len(hakkar_drops) > 0:
        droppers = ''
        for drop in hakkar_drops:
            if len(droppers) > 0:
                droppers += ',  '
            droppers += drop.time + ' (**' + drop.name + '**)'
        message += droppers
    else:
        message += '?:??'
    if len(hakkar_yi_summons) > 0:
        message += '  --  ' + await summoners_buffers_msg(hakkar_yi_summons, 'YI summons')
    if len(hakkar_bb_summons) > 0:
        message += '  --  ' + await summoners_buffers_msg(hakkar_bb_summons, 'BB summons')
    return message

async def calc_bvsf_msg():
    if await validate_time_format(bvsf_time):
        next_time_1 = await calculate_next_flower(bvsf_time)
        next_time_2 = await calculate_next_flower(next_time_1)
        message = ':wilted_rose:  BVSF --- ' + bvsf_time + ' -> ' + next_time_1 + ' -> ' + next_time_2
    else:
        message = ':wilted_rose:  BVSF --- ' + bvsf_time
    if len(bvsf_summons) > 0:
        message += '  --  ' + await summoners_buffers_msg(bvsf_summons)
    return message

async def calc_dmt_msg():
    message = await summoners_buffers_msg(dmt_buffs, 'DM buffs')
    if len(dmt_summons) > 0:
        if len(message) > 0:
            message += '  --  ' + await summoners_buffers_msg(dmt_summons)
        else:
            message = await summoners_buffers_msg(dmt_summons)
    if len(message) == 0:
        message = 'None available at this time'
    message = ':crown:  DMT --- ' + message
    return message

async def calc_naxx_msg():
    message = ''
    if len(naxx_summons) > 0:
        message = ':skull:  Naxx --- ' + await summoners_buffers_msg(naxx_summons) + '\n'
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
        message += await summoners_buffers_msg(dmf_summons)
    else:
        message += ' No summons available at this time'
    message += '\n'
    return message

async def check_for_bvsf_updates():
    global bvsf_time
    if not await validate_time_format(bvsf_time):
        return;
    local_time = await get_local_time()
    bvsf_date_time = datetime.strptime(bvsf_time, '%I:%M%p')
    new_time = local_time.replace(hour=bvsf_date_time.hour, minute=bvsf_date_time.minute)
    while local_time > new_time:
        new_time += timedelta(minutes=25)
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
            message += ' (**' + drop.name + '**)'
        else:
            message += ' (' + drop.time + ' - **' + drop.name + '**)'
    return message

async def summoners_buffers_msg(summoners, message_ending = 'summons'):
    message = ''
    if len(summoners) > 0:
        message += 'Whisper '
        for index in range(len(summoners)):
            summoner = summoners[index]
            if index > 0:
                message += '  |  '
            message += ' **' + summoner.name + '** '
            if len(summoner.msg) > 0:
                message += '(' + summoner.msg + ') '
        message += ' \'inv\' for {0}'.format(message_ending)
    return message

async def add_dropper(droppers, name, time):
    await add_dropper_no_post(droppers, name, time)
    await post_in_world_buffs_chat_channel()

async def add_dropper_no_post(droppers, name, time):
    for drop in droppers:
        if drop.name == name.title():
            drop.time = time
            return

    dropper = Dropper(time, name.title())
    droppers.append(dropper)

async def add_summoner_buffer(summoners_buffers, name, note, author=''):
    await add_summoner_buffer_no_post(summoners_buffers, name, note, author)
    await post_in_world_buffs_chat_channel()

async def add_summoner_buffer_no_post(summoners_buffers, name, note, author=''):
    message = await construct_args_message(note)
    if len(message) > 30:
        message = message[:30]
    for summon_buff in summoners_buffers:
        if summon_buff.name == name.title():
            summon_buff.msg = message
            return

    summoner_buffer = SummonerBuffer(name.title(), message, author)
    summoners_buffers.append(summoner_buffer)

async def remove_summoner_buffer_dropper(ctx, summoners_buffers_droppers, name):
    for summon_buff_drop in summoners_buffers_droppers:
        if summon_buff_drop.name == name.title():
            summoners_buffers_droppers.remove(summon_buff_drop)
            await post_in_world_buffs_chat_channel()
            return True

    await ctx.send('Name **{0}** not found - nothing to remove'.format(name))
    return False

async def has_rights_to_remove(summoners_buffers, name, author):
    has_rights = False
    for role in author.roles:
        if role.id == WORLD_BUFF_COORDINATOR_ROLE_ID:
            has_rights = True
            break
        elif role.id == WORLD_BUFF_SELLER_ROLE_ID:
            for summon_buff_drop in summoners_buffers:
                if summon_buff_drop.name == name.title() and (summon_buff_drop.author == '' or summon_buff_drop.author == author.id):
                    has_rights = True
                    break
    if not has_rights:
        raise commands.errors.MissingRole(WORLD_BUFF_COORDINATOR_ROLE_ID)
        return False
    return True

async def construct_args_message(args):
    message = ''
    for index in range(len(args)):
        if index > 0:
            message = message + ' '
        message += args[index]
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

async def playback_invalid_time_message(ctx):
    await ctx.send('Invalid time provided, format must be (H)H:MM[am|pm] - example: {0.prefix}{0.command.name} 2:54pm'.format(ctx))

async def playback_message(ctx, message):
    if (playback_updates):
        await ctx.send(message)

async def post_in_world_buffs_chat_channel():
    channel = bot.get_channel(WORLD_BUFF_CHANNEL_ID)
    messages = await channel.history(limit = 1).flatten()
    if len(messages) > 0 and messages[0].author == bot.user:
        message = await channel.fetch_message(messages[0].id)
        await message.edit(content = await get_buff_times())
    else:
        await channel.send(await get_buff_times())


# Sample Message to process
#Updated as of 2020-09-11 at 07:42am ST

#:tools: **SERVER IS UP** :tools:

#:japanese_ogre:  Rend --- 8:00am (8:05am - **Dajokerrrend**) (9:05am - **Norend**)
#:dragon:  Ony --- 8:05am (**Dajokerrrend**)
#:dragon_face:  Nef --- 9:09am (9:10am - **Dajokerrnef**)
#:heartpulse:  Hakkar --- 4:45pm (**Test**),  5:45pm (**Tester**)  --  Whisper  **Yisums** (1g)  'inv' for YI summons  --  Whisper  **Bbsums** (2g)  'inv' for BB summons
#:wilted_rose:  BVSF --- 5:10pm -> 5:35pm -> 6:00pm  --  Whisper  **Bvsfsums** (5g)  'inv' for summons
#:crown:  DMT --- Whisper  **Buffer** (5g)   |   **Betterbuffer** (10g w/summon + port)  'inv' for DM buffs  --  Whisper  **Dmtsums** (3g)  'inv' for summons
#:skull:  Naxx --- Whisper  **Naxxsum** (7g)  'inv' for summons
#:bug:  AQ Gates --- Whisper  **Aqsum** (7g)  'inv' for summons
#:mountain:  BRM --- Whisper  **Brmsums** (5g or 10g w/FR :fire_extinguisher:)  'inv' for summons
#:circus_tent:  DMF (Elwynn Forest) --- Whisper  **Dmfsums** (4g w/port)  'inv' for summons
#:warning:  ALLY ALL OVER

#:airplane: :heartpulse::wilted_rose::crown::bug: :mountain: Denmule selling 8g summons to all raid & buff locations. Whisper 'inv __' with destination (i.e. DMT, BVSF, YI, AQ, BWL, MC, Org, ZG)
async def populate_data_from_message(message):
    populate_success = True
    lines = message.split("\n")
    for index in range(len(lines)):
        line = lines[index]
        if line.startswith(':tools:'):
            #:tools: SERVER IS UP :tools:
            global server_maintenance
            strings = line.split(':tools:')
            non_bold_strings = strings[1].split('**')
            server_maintenance = non_bold_strings[1]
            if await get_maintenance() != line + '\n\n':
                populate_success = False
                print('server_status')
        elif line.startswith(':japanese_ogre:  Rend --- '):
            #:japanese_ogre:  Rend --- 8:00am (8:05am - **Dajokerrrend**) (9:05am - **Norend**)
            global rend_time
            global rend_drops
            strings = line.split(':japanese_ogre:  Rend --- ')
            parts = strings[1].split('(')
            rend_time = parts[0].strip()
            await process_droppers(rend_drops, parts[1:], rend_time)
            if await calc_rend_msg() != line:
                populate_success = False
                print('rend')
        elif line.startswith(':dragon:  Ony --- '):
            #:dragon:  Ony --- 8:05am (**Dajokerrrend**)
            global ony_time
            global ony_drops
            strings = line.split(':dragon:  Ony --- ')
            parts = strings[1].split('(')
            ony_time = parts[0].strip()
            await process_droppers(ony_drops, parts[1:], ony_time)
            if await calc_ony_msg() != line:
                populate_success = False
                print('ony')
        elif line.startswith(':dragon_face:  Nef --- '):
            #:dragon_face:  Nef --- 9:09am (9:10am - **Dajokerrnef**)
            global nef_time
            global nef_drops
            strings = line.split(':dragon_face:  Nef --- ')
            parts = strings[1].split('(')
            nef_time = parts[0].strip()
            await process_droppers(nef_drops, parts[1:], nef_time)
            if await calc_nef_msg() != line:
                populate_success = False
                print('nef')
        elif line.startswith(':heartpulse:  Hakkar --- '):
            #:heartpulse:  Hakkar --- 4:45pm (**Test**),  5:45pm (**Tester**)  --  Whisper  **Yisums** (1g)  'inv' for YI summons  --  Whisper  **Bbsums** (2g)  'inv' for BB summons
            global hakkar_drops
            global hakkar_yi_summons
            global hakkar_bb_summons
            strings = line.split(':heartpulse:  Hakkar --- ')
            parts = strings[1].split('  --  ')
            if parts[0] != '?:??':
                drops = parts[0].split(',')
                for drop in drops:
                    drop_parts = drop.split(' (')
                    drop_name = drop_parts[1].split('**')
                    await add_dropper_no_post(hakkar_drops, drop_name[1], drop_parts[0].strip())
            for summon_zone in parts[1:]:
                if 'YI summons' in summon_zone:
                    await process_summoners_buffers(hakkar_yi_summons, summon_zone)
                elif 'BB summons' in summon_zone:
                    await process_summoners_buffers(hakkar_bb_summons, summon_zone)
            if await calc_hakkar_msg() != line:
                populate_success = False
                print('hakkar')
        elif line.startswith(':wilted_rose:  BVSF --- '):
            #:wilted_rose:  BVSF --- 5:10pm -> 5:35pm -> 6:00pm  --  Whisper  **Bvsfsums** (5g)  'inv' for summons
            global bvsf_time
            global bvsf_summons
            strings = line.split(':wilted_rose:  BVSF --- ')
            parts = strings[1].split('  --  ')
            timer = parts[0].split(' ->')
            bvsf_time = timer[0]
            if len(parts) > 1:
                await process_summoners_buffers(bvsf_summons, parts[1])
            if await calc_bvsf_msg() != line:
                populate_success = False
                print('bvsf')
        elif line.startswith(':crown:  DMT --- '):
            #:crown:  DMT --- Whisper  **Buffer** (5g)   |   **Betterbuffer** (10g w/summon + port)  'inv' for DM buffs  --  Whisper  **Dmtsums** (3g)  'inv' for summons
            global dmt_buffs
            global dmt_summons
            strings = line.split(':crown:  DMT --- ')
            parts = strings[1].split('  --  ')
            for type in parts:
                if 'DM buffs' in type:
                    await process_summoners_buffers(dmt_buffs, type)
                elif 'for summons' in type:
                    await process_summoners_buffers(dmt_summons, type)
            if await calc_dmt_msg() != line:
                populate_success = False
                print('dmt')
        elif line.startswith(':skull:  Naxx --- '):
            #:skull:  Naxx --- Whisper  **Naxxsum** (7g)  'inv' for summons
            global naxx_summons
            strings = line.split(':skull:  Naxx --- ')
            if 'for summons' in strings[1]:
                await process_summoners_buffers(naxx_summons, strings[1])
            if await calc_naxx_msg() != line + '\n':
                populate_success = False
                print('naxx')
        elif line.startswith(':bug:  AQ Gates --- '):
            #:bug:  AQ Gates --- Whisper  **Aqsum** (7g)  'inv' for summons
            global aq_summons
            strings = line.split(':bug:  AQ Gates --- ')
            if 'for summons' in strings[1]:
                await process_summoners_buffers(aq_summons, strings[1])
            if await calc_aq_msg() != line + '\n':
                populate_success = False
                print('aq')
        elif line.startswith(':mountain:  BRM --- '):
            #:mountain:  BRM --- Whisper  **Brmsums** (5g or 10g w/FR :fire_extinguisher:)  'inv' for summons
            global brm_summons
            strings = line.split(':mountain:  BRM --- ')
            if 'for summons' in strings[1]:
                await process_summoners_buffers(brm_summons, strings[1])
            if await calc_brm_msg() != line + '\n':
                populate_success = False
                print('brm')
        elif line.startswith(':circus_tent:  DMF '):
            #:circus_tent:  DMF (Elwynn Forest) --- Whisper  **Dmfsums** (4g w/port)  'inv' for summons
            global dmf_location
            global dmf_summons
            strings = line.split(' --- ')
            if '(' in strings[0]:
                dmf_location = strings[0].split('(')[1].split(')')[0]
            if 'for summons' in strings[1]:
                await process_summoners_buffers(dmf_summons, strings[1])
            if await calc_dmf_msg() != line + '\n':
                populate_success = False
                print('dmf')
        elif line.startswith(':warning:'):
            #:warning:  ALLY ALL OVER
            global alliance
            strings = line.split(':warning:')
            alliance = strings[1].strip()
            if await get_alliance() != line + '\n':
                populate_success = False
                print('ally')
        elif index == len(lines) - 1:
            #:airplane: :heartpulse::wilted_rose::crown::bug: :mountain: Denmule selling 8g summons to all raid & buff locations. Whisper 'inv __' with destination (i.e. DMT, BVSF, YI, AQ, BWL, MC, Org, ZG)
            global extra_message
            if line != '':
                extra_message = line
                if await get_extra_message() != '\n' + line + '\n':
                    populate_success = False
                    print('extra_message')
    return populate_success

async def process_droppers(droppers, droppers_raw, drop_time):
    for drop in droppers_raw:
        if ' - ' in drop:
            drop_split = drop.split(' - ')
            await add_dropper_no_post(droppers, drop_split[1].split('**')[1], drop_split[0])
        else:
            await add_dropper_no_post(droppers, drop.split('**')[1], drop_time)

async def process_summoners_buffers(summoners_buffers, message):
    summoners_buffers_raw = message.split(' | ')
    for summoner_buffer in summoners_buffers_raw:
        parts = summoner_buffer.split('**')
        summoner_note = ''
        if '(' in parts[2] and ')' in parts[2]:
            index_start = parts[2].index('(') + 1
            index_end = parts[2].rindex(')')
            summoner_note = parts[2][index_start:index_end]
        await add_summoner_buffer_no_post(summoners_buffers, parts[1], [summoner_note])


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

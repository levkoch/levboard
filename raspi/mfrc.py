#!/usr/bin/env python
# -*- coding: utf8 -*-
#
#    Copyright 2014,2018 Mario Gomez <mario.gomez@teubi.co>
#
#    This file is part of MFRC522-Python
#    MFRC522-Python is a simple Python implementation for
#    the MFRC522 NFC Card Reader for the Raspberry Pi.
#
#    MFRC522-Python is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    MFRC522-Python is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with MFRC522-Python.  If not, see <http://www.gnu.org/licenses/>.
#
import RPi.GPIO as GPIO
import spidev
import signal
import time
import logging

class MFRC522:
    MAX_LEN = 16

    PCD_IDLE = 0x00
    PCD_AUTHENT = 0x0E
    PCD_RECEIVE = 0x08
    PCD_TRANSMIT = 0x04
    PCD_TRANSCEIVE = 0x0C
    PCD_RESETPHASE = 0x0F
    PCD_CALCCRC = 0x03

    PICC_REQIDL = 0x26
    PICC_REQALL = 0x52
    PICC_ANTICOLL = 0x93
    PICC_SElECTTAG = 0x93
    PICC_AUTHENT1A = 0x60
    PICC_AUTHENT1B = 0x61
    PICC_READ = 0x30
    PICC_WRITE = 0xA0
    PICC_DECREMENT = 0xC0
    PICC_INCREMENT = 0xC1
    PICC_RESTORE = 0xC2
    PICC_TRANSFER = 0xB0
    PICC_HALT = 0x50

    MI_OK = 0
    MI_NOTAGERR = 1
    MI_ERR = 2

    Reserved00 = 0x00
    CommandReg = 0x01
    CommIEnReg = 0x02
    DivlEnReg = 0x03
    CommIrqReg = 0x04
    DivIrqReg = 0x05
    ErrorReg = 0x06
    Status1Reg = 0x07
    Status2Reg = 0x08
    FIFODataReg = 0x09
    FIFOLevelReg = 0x0A
    WaterLevelReg = 0x0B
    ControlReg = 0x0C
    BitFramingReg = 0x0D
    CollReg = 0x0E
    Reserved01 = 0x0F

    Reserved10 = 0x10
    ModeReg = 0x11
    TxModeReg = 0x12
    RxModeReg = 0x13
    TxControlReg = 0x14
    TxAutoReg = 0x15
    TxSelReg = 0x16
    RxSelReg = 0x17
    RxThresholdReg = 0x18
    DemodReg = 0x19
    Reserved11 = 0x1A
    Reserved12 = 0x1B
    MifareReg = 0x1C
    Reserved13 = 0x1D
    Reserved14 = 0x1E
    SerialSpeedReg = 0x1F

    Reserved20 = 0x20
    CRCResultRegM = 0x21
    CRCResultRegL = 0x22
    Reserved21 = 0x23
    ModWidthReg = 0x24
    Reserved22 = 0x25
    RFCfgReg = 0x26
    GsNReg = 0x27
    CWGsPReg = 0x28
    ModGsPReg = 0x29
    TModeReg = 0x2A
    TPrescalerReg = 0x2B
    TReloadRegH = 0x2C
    TReloadRegL = 0x2D
    TCounterValueRegH = 0x2E
    TCounterValueRegL = 0x2F

    Reserved30 = 0x30
    TestSel1Reg = 0x31
    TestSel2Reg = 0x32
    TestPinEnReg = 0x33
    TestPinValueReg = 0x34
    TestBusReg = 0x35
    AutoTestReg = 0x36
    VersionReg = 0x37
    AnalogTestReg = 0x38
    TestDAC1Reg = 0x39
    TestDAC2Reg = 0x3A
    TestADCReg = 0x3B
    Reserved31 = 0x3C
    Reserved32 = 0x3D
    Reserved33 = 0x3E
    Reserved34 = 0x3F

    serNum = []

    def __init__(self, bus=0, device=0, spd=1000000, pin_mode=10, pin_rst=-1, debugLevel='WARNING'):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = spd

        self.logger = logging.getLogger('mfrc522Logger')
        self.logger.addHandler(logging.StreamHandler())
        level = logging.getLevelName(debugLevel)
        self.logger.setLevel(level)

        gpioMode = GPIO.getmode()
        
        if gpioMode is None:
            GPIO.setmode(pin_mode)
        else:
            pin_mode = gpioMode
            
        if pin_rst == -1:
            if pin_mode == 11:
                pin_rst = 15
            else:
                pin_rst = 22
 
        GPIO.setup(pin_rst, GPIO.OUT)
        GPIO.output(pin_rst, 1)
        self.MFRC522_Init()

    def MFRC522_Reset(self):
        self.Write_MFRC522(self.CommandReg, self.PCD_RESETPHASE)

    def Write_MFRC522(self, addr, val):
        val = self.spi.xfer2([(addr << 1) & 0x7E, val])

    def Read_MFRC522(self, addr):
        val = self.spi.xfer2([((addr << 1) & 0x7E) | 0x80, 0])
        return val[1]

    def Close_MFRC522(self):
        self.spi.close()
        GPIO.cleanup()

    def SetBitMask(self, reg, mask):
        tmp = self.Read_MFRC522(reg)
        self.Write_MFRC522(reg, tmp | mask)

    def ClearBitMask(self, reg, mask):
        tmp = self.Read_MFRC522(reg)
        self.Write_MFRC522(reg, tmp & (~mask))

    def AntennaOn(self):
        temp = self.Read_MFRC522(self.TxControlReg)
        if (~(temp & 0x03)):
            self.SetBitMask(self.TxControlReg, 0x03)

    def AntennaOff(self):
        self.ClearBitMask(self.TxControlReg, 0x03)

    def MFRC522_ToCard(self, command, sendData):
        backData = []
        backLen = 0
        status = self.MI_ERR
        irqEn = 0x00
        waitIRq = 0x00
        lastBits = None
        n = 0

        if command == self.PCD_AUTHENT:
            irqEn = 0x12
            waitIRq = 0x10
        if command == self.PCD_TRANSCEIVE:
            irqEn = 0x77
            waitIRq = 0x30

        self.Write_MFRC522(self.CommIEnReg, irqEn | 0x80)
        self.ClearBitMask(self.CommIrqReg, 0x80)
        self.SetBitMask(self.FIFOLevelReg, 0x80)

        self.Write_MFRC522(self.CommandReg, self.PCD_IDLE)

        for i in range(len(sendData)):
            self.Write_MFRC522(self.FIFODataReg, sendData[i])

        self.Write_MFRC522(self.CommandReg, command)

        if command == self.PCD_TRANSCEIVE:
            self.SetBitMask(self.BitFramingReg, 0x80)

        i = 2000
        while True:
            n = self.Read_MFRC522(self.CommIrqReg)
            i -= 1
            if ~((i != 0) and ~(n & 0x01) and ~(n & waitIRq)):
                break

        self.ClearBitMask(self.BitFramingReg, 0x80)

        if i != 0:
            if (self.Read_MFRC522(self.ErrorReg) & 0x1B) == 0x00:
                status = self.MI_OK

                if n & irqEn & 0x01:
                    status = self.MI_NOTAGERR

                if command == self.PCD_TRANSCEIVE:
                    n = self.Read_MFRC522(self.FIFOLevelReg)
                    lastBits = self.Read_MFRC522(self.ControlReg) & 0x07
                    if lastBits != 0:
                        backLen = (n - 1) * 8 + lastBits
                    else:
                        backLen = n * 8

                    if n == 0:
                        n = 1
                    if n > self.MAX_LEN:
                        n = self.MAX_LEN

                    for i in range(n):
                        backData.append(self.Read_MFRC522(self.FIFODataReg))
            else:
                status = self.MI_ERR

        return (status, backData, backLen)

    def Request(self, reqMode):
        status = None
        backBits = None
        TagType = []

        self.Write_MFRC522(self.BitFramingReg, 0x07)

        TagType.append(reqMode)
        (status, backData, backBits) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, TagType)

        if ((status != self.MI_OK) | (backBits != 0x10)):
            status = self.MI_ERR

        return (status, backBits)

    def MFRC522_Anticoll(self):
        backData = []
        serNumCheck = 0

        serNum = []

        self.Write_MFRC522(self.BitFramingReg, 0x00)

        serNum.append(self.PICC_ANTICOLL)
        serNum.append(0x20)

        (status, backData, backBits) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, serNum)

        if (status == self.MI_OK):
            i = 0
            if len(backData) == 5:
                for i in range(4):
                    serNumCheck = serNumCheck ^ backData[i]
                if serNumCheck != backData[4]:
                    status = self.MI_ERR
            else:
                status = self.MI_ERR

        return (status, backData)

    def CalulateCRC(self, pIndata):
        self.ClearBitMask(self.DivIrqReg, 0x04)
        self.SetBitMask(self.FIFOLevelReg, 0x80)

        for i in range(len(pIndata)):
            self.Write_MFRC522(self.FIFODataReg, pIndata[i])

        self.Write_MFRC522(self.CommandReg, self.PCD_CALCCRC)
        i = 0xFF
        while True:
            n = self.Read_MFRC522(self.DivIrqReg)
            i -= 1
            if not ((i != 0) and not (n & 0x04)):
                break
        pOutData = []
        pOutData.append(self.Read_MFRC522(self.CRCResultRegL))
        pOutData.append(self.Read_MFRC522(self.CRCResultRegM))
        return pOutData

    def MFRC522_SelectTag(self, serNum):
        backData = []
        buf = []
        buf.append(self.PICC_SElECTTAG)
        buf.append(0x70)
        
        for i in range(5):
            buf.append(serNum[i])

        pOut = self.CalulateCRC(buf)
        buf.append(pOut[0])
        buf.append(pOut[1])
        (status, backData, backLen) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, buf)

        if (status == self.MI_OK) and (backLen == 0x18):
            self.logger.debug("Size: " + str(backData[0]))
            return backData[0]
        else:
            return 0

    def MFRC522_Auth(self, authMode, BlockAddr, Sectorkey, serNum):
        buff = []

        # First byte should be the authMode (A or B)
        buff.append(authMode)

        # Second byte is the trailerBlock (usually 7)
        buff.append(BlockAddr)

        # Now we need to append the authKey which usually is 6 bytes of 0xFF
        for i in range(len(Sectorkey)):
            buff.append(Sectorkey[i])

        # Next we append the first 4 bytes of the UID
        for i in range(4):
            buff.append(serNum[i])

        # Now we start the authentication itself
        (status, backData, backLen) = self.MFRC522_ToCard(self.PCD_AUTHENT, buff)

        # Check if an error occurred
        if not (status == self.MI_OK):
            self.logger.error("AUTH ERROR!!")
        if not (self.Read_MFRC522(self.Status2Reg) & 0x08) != 0:
            self.logger.error("AUTH ERROR(status2reg & 0x08) != 0")

        # Return the status
        return status

    def MFRC522_StopCrypto1(self):
        self.ClearBitMask(self.Status2Reg, 0x08)

    def MFRC522_Read(self, blockAddr):
        recvData = []
        recvData.append(self.PICC_READ)
        recvData.append(blockAddr)
        pOut = self.CalulateCRC(recvData)
        recvData.append(pOut[0])
        recvData.append(pOut[1])
        (status, backData, backLen) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, recvData)
        if not (status == self.MI_OK):
            self.logger.error("Error while reading!")

        if len(backData) == 16:
            self.logger.debug("Sector " + str(blockAddr) + " " + str(backData))
            return backData
        else:
            return None

    def MFRC522_Write(self, blockAddr, writeData):
        buff = []
        buff.append(self.PICC_WRITE)
        buff.append(blockAddr)
        crc = self.CalulateCRC(buff)
        buff.append(crc[0])
        buff.append(crc[1])
        (status, backData, backLen) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, buff)
        if not (status == self.MI_OK) or not (backLen == 4) or not ((backData[0] & 0x0F) == 0x0A):
            status = self.MI_ERR

        self.logger.debug("%s backdata &0x0F == 0x0A %s" % (backLen, backData[0] & 0x0F))
        if status == self.MI_OK:
            buf = []
            for i in range(16):
                buf.append(writeData[i])

            crc = self.CalulateCRC(buf)
            buf.append(crc[0])
            buf.append(crc[1])
            (status, backData, backLen) = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, buf)
            if not (status == self.MI_OK) or not (backLen == 4) or not ((backData[0] & 0x0F) == 0x0A):
                self.logger.error("Error while writing")
            if status == self.MI_OK:
                self.logger.debug("Data written")


    def MFRC522_DumpClassic1K(self, key, uid):
        for i in range(64):
            status = self.MFRC522_Auth(self.PICC_AUTHENT1A, i, key, uid)
            # Check if authenticated
            if status == self.MI_OK:
                self.MFRC522_Read(i)
            else:
                self.logger.error("Authentication error")

    def MFRC522_Init(self):
        self.MFRC522_Reset()

        self.Write_MFRC522(self.TModeReg, 0x8D)
        self.Write_MFRC522(self.TPrescalerReg, 0x3E)
        self.Write_MFRC522(self.TReloadRegL, 30)
        self.Write_MFRC522(self.TReloadRegH, 0)

        self.Write_MFRC522(self.TxAutoReg, 0x40)
        self.Write_MFRC522(self.ModeReg, 0x3D)
        self.AntennaOn()

class MFRC:
    """
    A class for reading, writing and clearing data using the MFRC522 RFID module with extended function.

    Attributes:
        MFRC522 (module): The MFRC522 module used for communication with the RFID reader.
        KEY (list): The default authentication key used for reading and writing data.
    """
    def __init__(self, KEY=[0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]):
        """
        Initializes a BasicMFRC522 instance.

        Args:
            KEY (list): The authentication key used for reading and writing data.
        """
        self.MFRC522 = MFRC522()  # Create an instance of the MFRC522 class
        self.KEY = KEY  # Set the authentication key

    def read_sector(self, trailer_block):
        """
        Read data from a sector of the RFID tag.

        Args:
            trailer_block (int): The block number of the sector trailer.

        Returns:
            tuple: A tuple containing the tag ID (as an integer) and the data read (as a string).
        """
        id, text = self.read_no_block(trailer_block)
        while not id:
            id, text = self.read_no_block(trailer_block)
        return id, text

    def read_sectors(self, trailer_blocks):
        """
        Read data from multiple sectors of the RFID tag.

        Args:
            trailer_blocks (list): The list of block numbers of the sector trailers.

        Returns:
            tuple: A tuple containing the tag ID (as an integer) and the concatenated data read from all sectors (as a string).
        """
        text_all = ''
        for trailer_block in trailer_blocks:
            id, text = self.read_sector(trailer_block)
            text_all += text
        return id, text_all

    def read_id(self):
        """
        Read the tag ID from the RFID tag.

        Returns:
            int: The tag ID as an integer.
        """
        id = self.read_id_no_block()
        while not id:
            id = self.read_id_no_block()
        return id

    def read_id_no_block(self):
        """
        Attempt to read the tag ID from the RFID tag.

        Returns:
            int: The tag ID as an integer, or None if the operation fails.
        """
        # Send request to RFID tag
        (status, TagType) = self.MFRC522.Request(self.MFRC522.PICC_REQIDL)

        if status != self.MFRC522.MI_OK:
            return None

        # Anticollision, return UID if successful
        (status, uid) = self.MFRC522.Anticoll()
        if status != self.MFRC522.MI_OK:
            return None

        # Convert UID to integer and return as the tag ID
        return self._uid_to_num(uid)

    def read_no_block(self, trailer_block):
        """
        Attempt to read data from the RFID tag.

        Args:
            trailer_block (int): The block number of the sector trailer.
            block_addr (tuple): The block numbers of the data blocks to read.

        Returns:
            tuple: A tuple containing the tag ID (as an integer) and the data read (as a string),
                or (None, None) if the operation fails.
        """
        if not self._check_trailer_block(trailer_block):
            raise ValueError("Invalid Trailer Block {trailer_block}")

        block_addr = (trailer_block-3, trailer_block-2, trailer_block-1)

        # Send request to RFID tag
        (status, TagType) = self.MFRC522.Request(self.MFRC522.PICC_REQIDL)
        if status != self.MFRC522.MI_OK:
            return None, None

        # Anticollision, return UID if successful
        (status, uid) = self.MFRC522.Anticoll()
        if status != self.MFRC522.MI_OK:
            return None, None

        # Convert UID to integer and store as the tag ID
        id = self._uid_to_num(uid)

        # Select the RFID tag
        self.MFRC522.SelectTag(uid)

        # Authenticate with the tag using the provided key
        status = self.MFRC522.Authenticate(self.MFRC522.PICC_AUTHENT1A, trailer_block, self.KEY, uid)

        # Initialize variables for storing data and text read from the tag
        data = []
        text_read = ''

        try:
            if status == self.MFRC522.MI_OK:
                # Read data blocks specified by block_addr
                for block_num in block_addr:
                    block = self.MFRC522.ReadTag(block_num)
                    if block:
                        data += block

                # Convert data to string
                if data:
                    text_read = ''.join(chr(i) for i in data)

            # Stop cryptographic communication with the tag
            self.MFRC522.StopCrypto1()

            # Return the tag ID and the read data
            return id, text_read

        except:
            # Stop cryptographic communication with the tag in case of exception
            self.MFRC522.StopCrypto1()

            # Return None, None if an exception occurs
            return None, None
        
    def write_sector(self, text, trailer_block):
        """
        Write data to a sector of the RFID tag.

        Args:
            text (str): The data to write.
            trailer_block (int): The block number of the sector trailer.

        Returns:
            tuple: A tuple containing the tag ID (as an integer) and the data written (as a string).
        """

        # Write the data to the RFID tag using the helper function write_no_block
        id, text_in = self.write_no_block(text, trailer_block)

        # Retry writing if it fails initially
        while not id:
            id, text_in = self.write_no_block(text, trailer_block)

        # Return the tag ID and the written data
        return id, text_in

    def write_sectors(self, text, trailer_blocks):
        """
        Write data to multiple sectors of the RFID tag.

        Args:
            text (str): The data to write.
            trailer_blocks (list): The list of block numbers of the sector trailers.

        Returns:
            tuple: A tuple containing the tag ID (as an integer) and the concatenated data written to all sectors (as a string).
        """
        # Split the input text into chunks of 48 characters
        text_formated_list = self._split_string(text)

        # Initialize an empty string to store the concatenated data
        text_all = ''

        # Iterate through the trailer_blocks list
        for i in range(0, len(trailer_blocks)):
            try:
                # Write data to the sector using the write_sector function
                id, text = self.write_sector(text_formated_list[i], trailer_blocks[i])

                # Concatenate the written data to the text_all string
                text_all += text
            except IndexError:
                # Ignore any index errors that may occur if there are fewer chunks than trailer blocks
                pass

        # Return the tag ID and the concatenated data
        return id, text_all

    def write_no_block(self, text, trailer_block):
        """
        Attempt to write data to the RFID tag.

        Args:
            text (str): The data to write.
            trailer_block (int): The block number of the sector trailer.
            block_addr (tuple): The block numbers of the data blocks to write.

        Returns:
            tuple: A tuple containing the tag ID (as an integer) and the data written (as a string), or (None, None) if the operation fails.
        """
        if not self._check_trailer_block(trailer_block):
            raise ValueError("Invalid Trailer Block {trailer_block}")

        block_addr = (trailer_block-3, trailer_block-2, trailer_block-1)
        text = str(text)

        # Send request to RFID tag
        (status, TagType) = self.MFRC522.Request(self.MFRC522.PICC_REQIDL)
        if status != self.MFRC522.MI_OK:
            return None, None

        # Anticollision, return UID if success
        (status, uid) = self.MFRC522.Anticoll()
        if status != self.MFRC522.MI_OK:
            return None, None

        # Convert UID to integer and store as id
        id = self._uid_to_num(uid)

        # Select the RFID tag using the UID
        self.MFRC522.SelectTag(uid)

        # Authenticate with the sector trailer block using the default key
        status = self.MFRC522.Authenticate(self.MFRC522.PICC_AUTHENT1A, trailer_block, self.KEY, uid)

        # Read the sector trailer block
        self.MFRC522.ReadTag(trailer_block)

        try:
            if status == self.MFRC522.MI_OK:
                # Prepare the data to be written
                data = bytearray()
                data.extend(bytearray(text.ljust(len(block_addr) * 16).encode('ascii')))
                i = 0
                for block_num in block_addr:
                    # Write the data to the corresponding data blocks
                    self.MFRC522.WriteTag(block_num, data[(i*16):(i+1)*16])
                    i += 1

            # Stop encryption
            self.MFRC522.StopCrypto1()

            # Return the tag ID and the written data
            return id, text[0:(len(block_addr) * 16)]
        except:
            # Stop encryption and return None if an exception occurs
            self.MFRC522.StopCrypto1()
            return None, None

    def clear_sector(self, trailer_block):
        """
        Clear a sector of the RFID tag by writing zeros to all data blocks.

        Args:
            trailer_block (int): The block number of the sector trailer.

        Returns:
            int: The tag ID as an integer.
        """
        # Clear the sector using the clear_no_sector function
        id = self.clear_no_sector(trailer_block)

        # Retry clearing the sector until it succeeds and returns a tag ID
        while not id:
            id = self.clear_no_sector(trailer_block)

        # Return the tag ID
        return id

    def clear_sectors(self, trailer_blocks):
        """
        Clear multiple sectors of the RFID tag by writing zeros to all data blocks.

        Args:
            trailer_blocks (list): The list of block numbers of the sector trailers.

        Returns:
            int: The tag ID as an integer.
        """
        # Iterate through the trailer_blocks list and clear each sector
        for i in trailer_blocks:
            id = self.clear_sector(i)

        # Return the tag ID
        return id

    def clear_no_sector(self, trailer_block):
        """
        Clear a sector of the RFID tag by writing zeros to all data blocks.

        Args:
            trailer_block (int): The block number of the sector trailer.

        Returns:
            int: The tag ID as an integer, or None if the operation fails.
        """
        if not self._check_trailer_block(trailer_block):
            raise ValueError("Invalid Trailer Block {trailer_block}")

        block_addr = (trailer_block-3, trailer_block-2, trailer_block-1)

        # Send request to RFID tag
        (status, TagType) = self.MFRC522.Request(self.MFRC522.PICC_REQIDL)
        if status != self.MFRC522.MI_OK:
            return None

        # Anticollision, return UID if success
        (status, uid) = self.MFRC522.Anticoll()
        if status != self.MFRC522.MI_OK:
            return None

        # Convert UID to integer and store as id
        id = self._uid_to_num(uid)

        # Select the RFID tag using the UID
        self.MFRC522.SelectTag(uid)

        # Authenticate with the sector trailer block using the default key
        status = self.MFRC522.Authenticate(self.MFRC522.PICC_AUTHENT1A, trailer_block, self.KEY, uid)

        # Read the sector trailer block
        self.MFRC522.ReadTag(trailer_block)

        # Determine the block addresses of the data blocks in the sector

        try:
            if status == self.MFRC522.MI_OK:
                # Prepare data with all zeros
                data = [0x00]*16

                # Write zeros to each data block in the sector
                for block_num in block_addr:
                    self.MFRC522.WriteTag(block_num, data)

            # Stop encryption
            self.MFRC522.StopCrypto1()

            # Return the tag ID
            return id
        except:
            # Stop encryption and return None if an exception occurs
            self.MFRC522.StopCrypto1()
            return None

    def _check_trailer_block(self, trailer_block):
        if (trailer_block+1)%4 == 0:
            return True
        else:
            return False

    def _uid_to_num(self, uid):
        """
        Convert the UID (Unique Identifier) of the RFID tag to an integer.

        Args:
            uid (list): The UID as a list of bytes.

        Returns:
            int: The UID as an integer.
        """
        n = 0
        for i in range(0, 5):
            n = n * 256 + uid[i]
        return n

    def _split_string(self, string):
        """
        Split a string into chunks of 48 characters.

        Args:
            string (str): The string to split.

        Returns:
            list: A list of strings, each containing up to 48 characters.
        """
        l = list()
        for i in range(0, len(string), 48):
            l.append(string[i:i+48])

        # If the last chunk is less than 48 characters, pad it with null characters ('\0')
        if len(l[-1]) < 48:
            l[-1] += '\0'*(48-len(l[-1]))

        return l
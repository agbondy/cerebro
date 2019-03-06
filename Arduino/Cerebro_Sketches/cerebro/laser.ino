void triggerOne(unsigned int desiredPower,LaserDiode* thediode){
  uint32_t onClock,offClock,trainClock,delayClock;
  bool laserEnabled = true; //set flag for entering waveform loop
  bool newPulse = true;      //
  delayClock=millis();              //reset clocks
  if (waveform.startDelay>0){
    while ((millis()-delayClock)<waveform.startDelay){
      //wait. be ready to stop if interrupted.
    }
  }
  onClock=trainClock=millis();
  while(laserEnabled){
    //check if another command (abort or continuation) has been sent since the trigger was activated
    // reset clock on continuation. or abort waveform.
    if (radio.receiveDone()){
      if (radio.DATALEN == sizeof(integerMessage)){
        integerMessage = *(IntegerPayload*)radio.DATA;
        switch (integerMessage.variable){
          case 'A':
            reportLaserStats();
            laserEnabled = thediode->off();
            sendACK();
            break;
          case 'C':
            onClock=trainClock=millis();
            sendACK();
            break;
        }
      }
    }
    //else if onClock hasn't expired, turn on/keep on the laser
    else if ((millis()-onClock)<waveform.onTime){
      thediode->sendDAC(thediode->DAClevel);              //Laser on
      thediode->feedback(desiredPower);      //increase or decrease DAClevel to reach desired lightPower
      offClock = millis();
    }
    //else if offClock hasn't expired, turn off/keep off light
    else if((millis()-offClock)<waveform.offTime){
      if (newPulse){                   //if the laser is on then turn it off, otherwise do nothing (i.e. leave turned off)
        newPulse = thediode->off();         //laserOn = false
      }
    }
    //else if trainClock hasn't expired, restart the light pulse
    else if((millis()-trainClock)<waveform.trainDur){
      newPulse = true;
      onClock = millis();
    }
    //else the end of the waveform has been reached. turn off the light.
    else{
      reportLaserStats();
      if (waveform.rampDur>0){
        thediode->fade(waveform.rampDur);
      }
      laserEnabled = thediode->off();
    }
  }
}

void triggerBoth(){
  int countdownMS = Watchdog.enable(500);  
  uint32_t onClock,offClock,trainClock,delayClock;
  bool laserEnabled = true; //set flag for entering waveform loop
  bool newPulse = true;      //
  delayClock=millis();              //reset clocks
  if (waveform.startDelay>0){
    while ((millis()-delayClock)<waveform.startDelay){
      Watchdog.reset();            
      //wait. be ready to stop if interrupted.
    }
  }
  onClock=trainClock=millis();
  while(laserEnabled){
    Watchdog.reset();        
    //check if another command (abort or continuation) has been sent since the trigger was activated
    if (radio.receiveDone()){
      if (radio.DATALEN == sizeof(integerMessage)){
        integerMessage = *(IntegerPayload*)radio.DATA;
        switch (integerMessage.variable){
          case 'A':
            Watchdog.disable();              
            sendACK();
            checkForMiss();
            laserEnabled =  turnoff();
            break;
          case 'C':
            // Watchdog.reset();                        
            checkForMiss();
            onClock=trainClock=millis();
            break;
        }
      }
    }
    //else if onClock hasn't expired, turn on/keep on the laser
    else if ((millis()-onClock)<waveform.onTime){
      right.sendDAC(right.setPoint*3);
      //right.feedback(right.setPoint); //increase or decrease DAClevel to reach desired lightPower
      left.sendDAC(left.setPoint*3);
      //left.feedback(left.setPoint); //removed feedback AGB 2/2019
      offClock = millis();
    }
    //else if offClock hasn't expired, turn off/keep off light
    else if((millis()-offClock)<waveform.offTime){
      if (newPulse){                   //if the laser is on then turn it off, otherwise do nothing (i.e. leave turned off)
        newPulse = left.off();         //laserOn = false
        newPulse = right.off();         //laserOn = false
      }
    }
    //else if trainClock hasn't expired, restart the light pulse
    else if((millis()-trainClock)<waveform.trainDur){
      newPulse = true;
      onClock = millis();
    }
    //else the end of the waveform has been reached. turn off the light.
    else{
      Watchdog.disable();
      laserEnabled =  turnoff();
    }
  }
}

void reportLaserStats(){
  diodeStats.msgCount = msgCount;
  diodeStats.leftFBK = left.lastAnalogReading;
  diodeStats.rightFBK = right.lastAnalogReading;
  diodeStats.leftDAC = left.lastDAClevel;
  diodeStats.rightDAC = right.lastDAClevel;
  if (radio.sendWithRetry(BASESTATION, (const void*)(&diodeStats), sizeof(diodeStats))){
    Serial.println("laser stats sent");
  }
  else{
    Serial.println("laser stats send fail");
  }
}

bool turnoff(){
  diodeStats.msgCount = msgCount;
  diodeStats.leftFBK = left.lastAnalogReading;
  diodeStats.rightFBK = right.lastAnalogReading;
  diodeStats.leftDAC = left.lastDAClevel;
  diodeStats.rightDAC = right.lastDAClevel;
  if (waveform.rampDur>0){
    uint32_t fadeClock;
    for (int i = 99; i>-1;i--) {  //fade values are stored in addresses 16-216 (100 values,2 bytes each)
      fadeClock = millis();
      left.feedback(left.setPoint*i/100);
      left.sendDAC(left.DAClevel);
      right.feedback(right.setPoint*i/100);
      right.sendDAC(right.DAClevel);
      while((millis()-fadeClock)<(waveform.rampDur/100)){
        //wait
      }
    }
  }
  left.off();
  right.off();
  if (radio.sendWithRetry(BASESTATION, (const void*)(&diodeStats), sizeof(diodeStats))){
    Serial.println("laser stats sent");
  }
  else{
    Serial.println("laser stats send fail");
  }
  if (reportBatteryFlag || lipo.capacity(REMAIN)<15){
    reportBattery();
    reportBatteryFlag = false;
  }
  //send alert if feedbacks aren't what were expected
  return false;
}

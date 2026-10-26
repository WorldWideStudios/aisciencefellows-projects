#import <Foundation/Foundation.h>
#import <IOBluetooth/IOBluetooth.h>
#include <unistd.h>
#include <sys/select.h>
static void emit(NSDictionary *o) { NSData *d=[NSJSONSerialization dataWithJSONObject:o options:0 error:nil]; puts([[NSString alloc] initWithData:d encoding:NSUTF8StringEncoding].UTF8String); fflush(stdout); }
static void device(IOBluetoothDevice *d) { emit(@{@"event":@"device",@"address":d.addressString?:@"",@"name":d.name?:@"",@"paired":@(d.isPaired)}); }
@interface Delegate : NSObject <IOBluetoothDeviceInquiryDelegate,IOBluetoothRFCOMMChannelDelegate,IOBluetoothDevicePairDelegate>
@property BOOL done;
@property int status;
@property NSString *pin;
@end
@implementation Delegate
- (void)devicePairingPINCodeRequest:(id)sender { BluetoothPINCode code={0}; NSData *bytes=[self.pin dataUsingEncoding:NSASCIIStringEncoding]; memcpy(&code,bytes.bytes,MIN(bytes.length,16)); [sender replyPINCode:bytes.length PINCode:&code]; }
- (void)devicePairingFinished:(id)sender error:(IOReturn)e { self.status=e; self.done=YES; emit(@{@"event":@"pair_complete",@"status":@(e)}); }
- (void)devicePairingUserConfirmationRequest:(id)sender numericValue:(BluetoothNumericValue)n { [sender replyUserConfirmation:NO]; emit(@{@"event":@"error",@"message":@"Numeric comparison required. Complete pairing in macOS Bluetooth settings."}); }

- (void)deviceInquiryDeviceFound:(IOBluetoothDeviceInquiry*)s device:(IOBluetoothDevice*)d { device(d); }
- (void)deviceInquiryDeviceNameUpdated:(IOBluetoothDeviceInquiry*)s device:(IOBluetoothDevice*)d devicesRemaining:(uint32_t)n { device(d); }
- (void)deviceInquiryComplete:(IOBluetoothDeviceInquiry*)s error:(IOReturn)e aborted:(BOOL)a { emit(@{@"event":@"scan_complete",@"status":@(e)}); self.done=YES; }
- (void)rfcommChannelData:(IOBluetoothRFCOMMChannel*)c data:(void*)p length:(size_t)n { NSMutableString *h=[NSMutableString string]; for(size_t i=0;i<n;i++) [h appendFormat:@"%02x",((unsigned char*)p)[i]]; emit(@{@"event":@"rx",@"hex":h}); }
- (void)rfcommChannelClosed:(IOBluetoothRFCOMMChannel*)c { emit(@{@"event":@"closed"}); self.done=YES; }
@end
int main(int argc,const char **argv) { @autoreleasepool {
 Delegate *d=[Delegate new];
 if(argc<2) { fprintf(stderr,"Usage: bluetooth scan | paired | connect ADDRESS [CHANNEL]\n"); return 2; }
 NSString *mode=@(argv[1]);
 if([mode isEqual:@"paired"] || [mode isEqual:@"scan"]) {
  for(IOBluetoothDevice *v in IOBluetoothDevice.pairedDevices) device(v);
  if([mode isEqual:@"paired"]) return 0;
  IOBluetoothDeviceInquiry *q=[IOBluetoothDeviceInquiry inquiryWithDelegate:d]; q.inquiryLength=10; q.updateNewDeviceNames=NO;
  IOReturn e=[q start]; if(e) { emit(@{@"event":@"error",@"status":@(e)}); return 1; }
  NSDate *deadline=[NSDate dateWithTimeIntervalSinceNow:25];
  while(!d.done && deadline.timeIntervalSinceNow>0) [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:.02]];
  if(!d.done) { [q stop]; emit(@{@"event":@"error",@"message":@"Discovery timed out; check macOS Bluetooth permission"}); return 1; } return 0;
 }
 if([mode isEqual:@"pair"] && argc>=3) {
  IOBluetoothDevice *target=[IOBluetoothDevice deviceWithAddressString:@(argv[2])]; if(!target) return 2;
  if(target.isPaired) {emit(@{@"event":@"pair_complete",@"status":@0});return 0;}
  d.pin=argc>3?@(argv[3]):@"12345";
  NSData *pinBytes=[d.pin dataUsingEncoding:NSASCIIStringEncoding]; if(!pinBytes || pinBytes.length<1 || pinBytes.length>16) return 2;
  IOBluetoothDevicePair *pair=[IOBluetoothDevicePair pairWithDevice:target]; pair.delegate=d;
  IOReturn e=[pair start]; if(e) {emit(@{@"event":@"error",@"status":@(e)});return 1;}
  NSDate *deadline=[NSDate dateWithTimeIntervalSinceNow:40];
  while(!d.done && deadline.timeIntervalSinceNow>0) [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:.02]];
  if(!d.done) { [pair stop];emit(@{@"event":@"error",@"message":@"Pairing timed out. Use macOS Bluetooth settings."});return 1;}
  return d.status?1:0;
 }
 if(![mode isEqual:@"connect"] || argc<3) return 2;
 IOBluetoothDevice *v=[IOBluetoothDevice deviceWithAddressString:@(argv[2])]; if(!v) return 2;
 BluetoothRFCOMMChannelID channel=1;
 IOBluetoothSDPServiceRecord *service=[v getServiceRecordForUUID:[IOBluetoothSDPUUID uuid16:0x1101]];
 if(service) [service getRFCOMMChannelID:&channel];
 if(argc>3) { int n=atoi(argv[3]); if(n<1||n>30) return 2; channel=n; }
 IOBluetoothRFCOMMChannel *c=nil; IOReturn e=[v openRFCOMMChannelSync:&c withChannelID:channel delegate:d];
 if(e || !c) { emit(@{@"event":@"error",@"status":@(e),@"message":@"RFCOMM open failed. Pair this pipette in macOS Bluetooth settings; enable its communication mode."}); return 1; }
 emit(@{@"event":@"ready",@"channel":@(channel),@"address":v.addressString});
 NSMutableData *input=[NSMutableData data];
 while(!d.done) {
  [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:.01]];
  fd_set f; FD_ZERO(&f); FD_SET(0,&f); struct timeval t={0,0};
  if(select(1,&f,NULL,NULL,&t)>0) {
   unsigned char b[2048]; ssize_t n=read(0,b,sizeof(b)); if(n<=0) break; [input appendBytes:b length:n];
   while(YES) {
    const unsigned char *p=input.bytes; NSUInteger k=0; while(k<input.length && p[k]!='\n') k++; if(k==input.length) break;
    NSString *line=[[NSString alloc] initWithBytes:p length:k encoding:NSUTF8StringEncoding]; [input replaceBytesInRange:NSMakeRange(0,k+1) withBytes:NULL length:0];
    NSMutableData *out=[NSMutableData data]; BOOL valid=line && line.length>0 && line.length%2==0 && line.length<=8192;
    for(NSUInteger j=0;valid && j<line.length;j+=2) { NSString *s=[line substringWithRange:NSMakeRange(j,2)]; NSScanner *sc=[NSScanner scannerWithString:s]; unsigned x; if(![sc scanHexInt:&x] || !sc.isAtEnd) {valid=NO;break;} unsigned char z=x; [out appendBytes:&z length:1]; }
    if(!valid) {emit(@{@"event":@"error",@"message":@"Invalid hex input"});continue;}
    IOReturn w=[c writeSync:out.mutableBytes length:(UInt16)out.length]; emit(@{@"event":@"write",@"status":@(w)});
   }
  }
 }
 [c closeChannel]; return 0;
}}

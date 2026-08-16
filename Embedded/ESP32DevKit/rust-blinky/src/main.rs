#![no_std]
#![no_main]

use esp_backtrace as _;
use esp_hal::delay::Delay;
use esp_hal::gpio::{Io, Level, Output};
use esp_hal::prelude::*;
use esp_println::println;

#[entry]
fn main() -> ! {
    let peripherals = esp_hal::init(esp_hal::Config::default());

    let io = Io::new(peripherals.GPIO, peripherals.IO_MUX);
    let mut led = Output::new(io.pins.gpio2, Level::Low);
    let delay = Delay::new();

    println!("ESP32 Rust blinky booting on GPIO2");

    loop {
        led.toggle();
        println!("tick");
        delay.delay_millis(500u32);
    }
}

//! Conservative OCR comparison. Never use symbolic equivalence as source truth.
//! Input TSV: id, hex-UTF8 candidate A, hex-UTF8 candidate B.
//! Output TSV: id, exact|format_only|different, token-edit-distance, max-tokens.
use std::io::{self, BufRead};

fn tokens(s: &str) -> Vec<String> {
    let chars: Vec<char> = s.chars().collect();
    let mut out=Vec::new(); let mut i=0;
    while i<chars.len() {
        let c=chars[i];
        if c.is_whitespace() {i+=1;continue;}
        if c=='\\' {
            let start=i; i+=1;
            if i<chars.len() && chars[i].is_ascii_alphabetic() {
                while i<chars.len() && chars[i].is_ascii_alphabetic() {i+=1;}
            } else if i<chars.len() {i+=1;}
            let token:String=chars[start..i].iter().collect();
            if !["\\left","\\right","\\,","\\;","\\!","\\quad","\\qquad","\\displaystyle"].contains(&token.as_str()) {out.push(token);}
        } else {out.push(c.to_string());i+=1;}
    }
    out
}
fn distance(a: &[String],b:&[String])->usize {
    let mut prev:Vec<usize>=(0..=b.len()).collect();
    for (i,x) in a.iter().enumerate() {
        let mut row=vec![i+1;b.len()+1];
        for (j,y) in b.iter().enumerate() {
            row[j+1]=(prev[j]+usize::from(x!=y)).min(prev[j+1]+1).min(row[j]+1);
        }
        prev=row;
    }
    prev[b.len()]
}
fn decode(s:&str)->Result<String,String> {
    if s.len()%2!=0 {return Err("odd hex length".into());}
    let bytes=(0..s.len()).step_by(2).map(|i|u8::from_str_radix(&s[i..i+2],16)
       .map_err(|e|e.to_string())).collect::<Result<Vec<_>,_>>()?;
    String::from_utf8(bytes).map_err(|e|e.to_string())
}
fn main()->Result<(),String> {
    for line in io::stdin().lock().lines() {
        let line=line.map_err(|e|e.to_string())?;
        let p:Vec<_>=line.split('\t').collect();
        if p.len()!=3 {return Err("expected id and two hex strings".into());}
        let a=decode(p[1])?;let b=decode(p[2])?;
        let at=tokens(&a);let bt=tokens(&b);
        let status=if a==b {"exact"} else if at==bt {"format_only"} else {"different"};
        println!("{}\t{}\t{}\t{}",p[0],status,distance(&at,&bt),at.len().max(bt.len()));
    }
    Ok(())
}
#[cfg(test)] mod tests {
    use super::*;
    #[test] fn harmless_spacing(){assert_eq!(tokens(r"\left( x + y \right)"),tokens("(x+y)"));}
    #[test] fn preserves_minus(){assert_ne!(tokens("a-b"),tokens("a+b"));}
    #[test] fn preserves_derivative(){assert_ne!(tokens("y'"),tokens("y"));}
    #[test] fn preserves_index(){assert_ne!(tokens("a_{ij}"),tokens("a_{ji}"));}
    #[test] fn preserves_exponent(){assert_ne!(tokens("h^2"),tokens("h^3"));}
    #[test] fn preserves_command_boundary(){assert_ne!(tokens(r"\sin x"),tokens(r"\sinx"));}
    #[test] fn no_algebraic_rewriting(){assert_ne!(tokens("a+b"),tokens("b+a"));}
    #[test] fn distance_counts_sign_change(){assert_eq!(distance(&tokens("a-b"),&tokens("a+b")),1);}
    #[test] fn malformed_hex_rejected(){assert!(decode("f").is_err());assert!(decode("zz").is_err());}
}

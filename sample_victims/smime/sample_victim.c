#include <stdio.h>
#include <stdlib.h>
#include <openssl/md5.h>
#include <string.h>

// gcc -g -Wall -o sample_victim sample_victim.c -lssl -lcrypto
// cert passphrase is 1234 for those to lazy to generate their own
// Sign S/MIME: openssl smime -sign -signer cert.pem  -inkey key.pem -in data.hash -out manifest.sig
// Verify S/MIME: openssl smime -verify -in manifest.sig -certfile cert.pem -noverify -out tmp.hash

int main(int argc, char** argv)
{
    unsigned char c[MD5_DIGEST_LENGTH];
    char ch;
    char filename[200];
    char openssl_command[400];
    char *out_filename = "sample_victim.output";
    int i;
    FILE *inFile;
    FILE *outFile = fopen(out_filename,"a");
    FILE *sigFile;
    MD5_CTX mdContext;
    int bytes;
    int ret;
    unsigned char data[1024];
    char d[3];
    char char_hash[1024];
    char manifest_hash[33] = {0};
    int matches = 1;


    memset(char_hash,0,1024);
    if (argc < 2){
        printf("[!] You need to specify the folder where the 'data.txt' and 'manifest.sig' files can be found! (including the last slash since I am lazy)\n");
        printf("[*] Example: ./%s /hello/world/\n",argv[0]);
        return 1;
    }
    snprintf(filename,199,"%sdata.txt",argv[1]);
    snprintf(openssl_command,399,"openssl smime -verify -in %smanifest.sig -certfile %scert.pem -noverify -out tmp.hash >/dev/null 2>&1",argv[1],argv[1]);
    inFile = fopen(filename, "rb");
    if (inFile == NULL) {
        printf ("%s can't be opened.\n", filename);
        return 0;
    }
    MD5_Init (&mdContext);
    while ((bytes = fread(data, 1, 1024, inFile)) != 0)
        MD5_Update(&mdContext, data, bytes);
    MD5_Final(c,&mdContext);
    for(i = 0; i < MD5_DIGEST_LENGTH; i++) {
        sprintf(d,"%02x", c[i]);
        char_hash[i*2] = d[0];
        char_hash[i*2+1] = d[1];
    }
    printf("[*] MD5 hash calculated: %s\n",char_hash);
    
    printf("[*] Verifying authenticity of the package hashes ... \n");
    // Hardcoded values in the command below!
    ret=system(openssl_command);
    if (ret >> 8 == 0){
        // validation successfull -> extract the contents of the file to tmp.hash and read it to manifest_hash variable
        sigFile = fopen("tmp.hash","r");
        fread(manifest_hash, 1, 32, sigFile);
    } else {
        printf("[!] S/MIME manifest file siganture verification failed!\n");
        return 1;
    }

    fseek(inFile, -32, SEEK_END); 
    matches = 1;
    for(i = 0; i < 32; i++) {
        if (char_hash[i] != manifest_hash[i]){
            matches = 0;
            break;
        }
    }
    // If we have match write a file with the inFile contents
    if (matches == 1){
        printf("[*] Everything seems legit ... writing output to %s ... \n",out_filename);
        // HASH verified this should only happen when "signature" validation completed successfully
        if ( fseek(inFile, 0L, SEEK_SET) != 0 ) { 
            printf("[!] SEEK failed.\n");
            return 0;
        }
        //inFile = fopen(filename, "rb");
        ch = fgetc(inFile) ;
        while( ch != EOF) {
            fputc(ch,outFile);
            ch = fgetc(inFile);
	    if (feof(inFile))
		    break;
        }
        fclose(inFile);
    } else {
        // If the hash does not match just shout
        printf("[!] Data hash does not match the hash mentioned in manifest! Not writing ANYTHING!\n");
    }
    fclose(outFile);
    return 0;
}

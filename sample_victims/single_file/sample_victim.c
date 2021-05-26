#include <stdio.h>
#include <stdlib.h>
#include <openssl/md5.h>
#include <string.h>

//gcc -g -Wall -o sample_victim sample_victim.c -lssl -lcrypto

int main(int argc, char** argv)
{
    unsigned char c[MD5_DIGEST_LENGTH];
    char ch;
    char *filename=argv[1];
    char *out_filename = "sample_victim.output";
    int i;
    unsigned long file_size;
    FILE *inFile = fopen(filename, "rb");
    FILE *outFile = fopen(out_filename,"a");
    MD5_CTX mdContext;
    int bytes;
    unsigned char data[1024];
    char d[3];
    char char_hash[1024];
    char append_hash[33] = {0};
    int matches = 1;
    int read_modulo = 0;
    int read_counter = 0;
    int read_max = 0;

    memset(char_hash,0,1024);
    if (argc != 2) {
        printf("[*] Usage: %s <data_file>\n",argv[0]);
        return 0;
    }
    if (inFile == NULL) {
        printf ("Either %s can't be opened.\n", filename);
        return 0;
    }
    MD5_Init (&mdContext);
    fseek(inFile, -32, SEEK_END);
    file_size = ftell(inFile);
    fseek(inFile, 0L, SEEK_SET);
    read_max = (file_size) / 1024;
    read_modulo = (file_size) % 1024;
    // Calculate MD5 and convert it to hexstring
    printf("[*] Calculating MD5 hash of the \"%s\" file ... \n",filename);
    
    for (read_counter = 0; read_counter < read_max; read_counter++){
        bytes = fread(data, 1, 1024, inFile);
        MD5_Update(&mdContext, data, bytes);
    }
    if ((bytes = fread(data, 1, read_modulo, inFile)) != 0) {       
        MD5_Update(&mdContext, data, bytes);
    }
    MD5_Final(c,&mdContext);
    for(i = 0; i < MD5_DIGEST_LENGTH; i++) {
        sprintf(d,"%02x", c[i]);
        char_hash[i*2] = d[0];
        char_hash[i*2+1] = d[1];
    }
    printf("[*] MD5 hash calculated: %s\n",char_hash);
    
    printf("[*] Verifying authenticity of the package hashes ... \n");
    fseek(inFile, -32, SEEK_END); 
    fread(append_hash, 1, 32, inFile);
    printf("[*] Extracted file hash from the end of the file: %s\n", append_hash); 
    matches = 1;
    for(i = 0; i < 32; i++) {
        if (char_hash[i] != append_hash[i]){
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
